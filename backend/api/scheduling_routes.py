from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.session import get_db
from backend.database.models import Appointment, Doctor, Slot, TriageNote
from backend.services.scheduling import scheduling_service

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])

class SlotHoldRequest(BaseModel):
    slot_id: int
    call_id: str
    ttl: Optional[int] = 180

class BookingConfirmRequest(BaseModel):
    call_id: str
    slot_id: int
    patient_name: str
    patient_age: int
    caller_phone: str
    department: str
    triage_data: Optional[Dict[str, Any]] = None

@router.get("/departments")
async def list_departments(db: AsyncSession = Depends(get_db)):
    stmt = select(Doctor.department).where(Doctor.is_active == True).distinct()
    res = await db.execute(stmt)
    depts = [row[0] for row in res.all()]
    return {"departments": sorted(depts)}

@router.get("/slots")
async def list_available_slots(department: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    slots = await scheduling_service.get_available_slots(db, department=department)
    return {"slots": slots, "count": len(slots)}

@router.post("/hold")
async def hold_slot(req: SlotHoldRequest, db: AsyncSession = Depends(get_db)):
    result = await scheduling_service.hold_slot(db, slot_id=req.slot_id, call_id=req.call_id, ttl=req.ttl)
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error"))
    return result

@router.post("/confirm")
async def confirm_booking(req: BookingConfirmRequest, db: AsyncSession = Depends(get_db)):
    result = await scheduling_service.confirm_booking(
        db=db,
        call_id=req.call_id,
        slot_id=req.slot_id,
        patient_name=req.patient_name,
        patient_age=req.patient_age,
        caller_phone=req.caller_phone,
        department=req.department,
        triage_data=req.triage_data
    )
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error"))
    return result

@router.get("/token/{token_id}")
async def get_patient_token_status(token_id: str, db: AsyncSession = Depends(get_db)):
    """
    Patient Portal Public Endpoint (No Login Required).
    Returns real-time status for the specified token ID only.
    Zero access to other patient data.
    """
    token_clean = token_id.strip().upper()
    stmt = (
        select(Appointment, Doctor, Slot)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Slot, Appointment.slot_id == Slot.id)
        .where(Appointment.token_id == token_clean)
    )
    res = await db.execute(stmt)
    row = res.first()

    if not row:
        raise HTTPException(status_code=404, detail="Token not found. Please verify your token ID format (e.g. CARD-20261020-001).")

    apt, doctor, slot = row

    # Calculate real-time active queue position ahead of this patient
    q_ahead_stmt = select(func.count(Appointment.id)).where(
        and_(
            Appointment.doctor_id == doctor.id,
            Appointment.status.in_(["SCHEDULED", "IN_QUEUE"]),
            Appointment.booked_at < apt.booked_at
        )
    )
    q_res = await db.execute(q_ahead_stmt)
    ahead_count = q_res.scalar() or 0
    current_live_pos = ahead_count + 1 if apt.status in ["SCHEDULED", "IN_QUEUE"] else 0

    return {
        "token_id": apt.token_id,
        "patient_name": apt.patient_name,
        "department": apt.department,
        "doctor_name": doctor.name,
        "doctor_specialization": doctor.specialization,
        "room_number": doctor.room_number,
        "slot_time": slot.slot_timestamp.isoformat(),
        "status": apt.status,
        "queue_position": current_live_pos if apt.status in ["SCHEDULED", "IN_QUEUE"] else "N/A",
        "patients_ahead": ahead_count,
        "booked_at": apt.booked_at.isoformat(),
        "follow_up_status": apt.follow_up_status
    }
