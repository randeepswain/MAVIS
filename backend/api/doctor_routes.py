import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.session import get_db
from backend.database.models import User, Doctor, Appointment, Slot, TriageNote, FollowUpRecord
from backend.api.auth import require_roles
from backend.agents.follow_up_agent import follow_up_agent
from backend.services.audit import audit_service

router = APIRouter(prefix="/doctor", tags=["Doctor Portal"])

class UpdateStatusRequest(BaseModel):
    status: str # 'IN_QUEUE', 'IN_CONSULTATION', 'COMPLETED', 'CANCELLED'
    consultation_notes: Optional[str] = None

class TriggerFollowUpRequest(BaseModel):
    simulated_patient_response: Optional[str] = None

@router.get("/queue")
async def get_doctor_queue(
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    # Find doctor record associated with this user
    doc_stmt = select(Doctor).where(Doctor.user_id == current_user.id)
    doc_res = await db.execute(doc_stmt)
    doctor = doc_res.scalars().first()

    if not doctor and current_user.role != "ADMIN":
        raise HTTPException(status_code=404, detail="Doctor profile not mapped to this user account.")

    # If admin testing doctor route, take the first doctor
    if not doctor and current_user.role == "ADMIN":
        doctor = (await db.execute(select(Doctor))).scalars().first()

    stmt = (
        select(Appointment, Slot, TriageNote)
        .join(Slot, Appointment.slot_id == Slot.id)
        .outerjoin(TriageNote, Appointment.id == TriageNote.appointment_id)
        .where(Appointment.doctor_id == doctor.id)
        .order_by(Slot.slot_timestamp.asc())
    )
    res = await db.execute(stmt)
    appointments = []
    for apt, slot, triage in res.all():
        appointments.append({
            "appointment_id": apt.id,
            "token_id": apt.token_id,
            "patient_name": apt.patient_name,
            "patient_age": apt.patient_age,
            "caller_phone": apt.caller_phone,
            "slot_time": slot.slot_timestamp.isoformat(),
            "status": apt.status,
            "queue_position": apt.queue_position,
            "follow_up_status": apt.follow_up_status,
            "consultation_notes": apt.consultation_notes,
            "urgency_level": triage.urgency_level if triage else "ROUTINE",
            "chief_complaint": triage.chief_complaint if triage else "N/A",
            "duration": triage.duration if triage else "N/A",
            "severity_scale": triage.severity_scale if triage else 5,
            "has_brief": triage is not None
        })

    return {
        "doctor_name": doctor.name,
        "department": doctor.department,
        "room_number": doctor.room_number,
        "queue": appointments
    }

@router.get("/brief/{appointment_id}")
async def get_clinical_handoff_brief(
    appointment_id: int,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(TriageNote, Appointment, Doctor, Slot)
        .join(Appointment, TriageNote.appointment_id == Appointment.id)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Slot, Appointment.slot_id == Slot.id)
        .where(TriageNote.appointment_id == appointment_id)
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row:
        raise HTTPException(status_code=404, detail="Clinical brief not found for this appointment.")

    triage, apt, doctor, slot = row
    return {
        "appointment_id": apt.id,
        "token_id": apt.token_id,
        "patient_name": apt.patient_name,
        "patient_age": apt.patient_age,
        "doctor_name": doctor.name,
        "department": doctor.department,
        "slot_time": slot.slot_timestamp.isoformat(),
        "chief_complaint": triage.chief_complaint,
        "duration": triage.duration,
        "severity_scale": triage.severity_scale,
        "urgency_level": triage.urgency_level,
        "triage_confidence": triage.triage_confidence,
        "department_rationale": triage.department_rationale,
        "handoff_brief": triage.handoff_brief,
        "created_at": triage.created_at.isoformat()
    }

@router.post("/appointment/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int,
    req: UpdateStatusRequest,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    res = await db.execute(stmt)
    apt = res.scalars().first()

    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    apt.status = req.status
    if req.consultation_notes:
        apt.consultation_notes = req.consultation_notes

    await audit_service.log_event(
        db=db,
        event_type="APPOINTMENT_STATUS_UPDATED",
        call_id=apt.call_id,
        payload_data={
            "appointment_id": apt.id,
            "token_id": apt.token_id,
            "new_status": req.status,
            "updated_by": current_user.email
        }
    )
    await db.commit()

    return {"success": True, "token_id": apt.token_id, "new_status": apt.status}

@router.post("/appointment/{appointment_id}/trigger-followup")
async def trigger_followup(
    appointment_id: int,
    req: TriggerFollowUpRequest,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes or simulates the F5 Post-Visit Follow-Up Agent interaction.
    """
    sample_response = req.simulated_patient_response or "My knee pain is much better now, swelling has gone down."
    result = await follow_up_agent.evaluate_patient_response(
        db=db,
        appointment_id=appointment_id,
        patient_utterance=sample_response
    )
    return result

@router.get("/followups")
async def get_doctor_followups(
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    # Fetch all follow-up records
    stmt = (
        select(FollowUpRecord, Appointment)
        .join(Appointment, FollowUpRecord.appointment_id == Appointment.id)
        .order_by(desc(FollowUpRecord.created_at))
    )
    res = await db.execute(stmt)
    records = []
    for fu, apt in res.all():
        records.append({
            "follow_up_id": fu.id,
            "appointment_id": apt.id,
            "token_id": apt.token_id,
            "patient_name": apt.patient_name,
            "scheduled_at": fu.scheduled_at.isoformat(),
            "executed_at": fu.executed_at.isoformat() if fu.executed_at else None,
            "patient_feedback": fu.patient_feedback,
            "recovery_condition": fu.recovery_condition,
            "escalated_to_doctor": fu.escalated_to_doctor,
            "doctor_alert_notes": fu.doctor_alert_notes
        })
    return {"follow_ups": records}
