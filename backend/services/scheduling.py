import asyncio
import datetime
import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.models import Doctor, Slot, Appointment, TriageNote
from backend.services.redis_service import redis_service
from backend.services.audit import audit_service

logger = logging.getLogger("mavis.scheduling")

DEPT_PREFIXES = {
    "Cardiology": "CARD",
    "Neurology": "NEUR",
    "Orthopedics": "ORTH",
    "Pulmonology": "PULM",
    "Gastroenterology": "GAST",
    "General Medicine": "GENM",
    "Dermatology": "DERM",
    "Ophthalmology": "OPHT",
    "ENT": "ENTD",
    "Pediatrics": "PEDI",
    "Emergency": "EMRG"
}

_scheduling_tx_lock = asyncio.Lock()

class SchedulingService:
    @staticmethod
    def get_department_prefix(department: str) -> str:
        return DEPT_PREFIXES.get(department, department[:4].upper())

    @staticmethod
    async def get_available_slots(db: AsyncSession, department: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves upcoming unbooked slots, filtering out slots currently under soft-hold.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        stmt = (
            select(Slot, Doctor)
            .join(Doctor, Slot.doctor_id == Doctor.id)
            .where(
                and_(
                    Slot.is_booked == False,
                    Slot.slot_timestamp >= now,
                    Doctor.is_active == True
                )
            )
            .order_by(Slot.slot_timestamp.asc())
        )
        if department and department != "All":
            stmt = stmt.where(Doctor.department.ilike(f"%{department}%"))

        res = await db.execute(stmt)
        slots_data = []
        for slot, doctor in res.all():
            holder = await redis_service.get_slot_hold_caller(slot.id)
            slots_data.append({
                "slot_id": slot.id,
                "doctor_id": doctor.id,
                "doctor_name": doctor.name,
                "department": doctor.department,
                "room_number": doctor.room_number,
                "slot_timestamp": slot.slot_timestamp.isoformat(),
                "is_held": holder is not None,
                "held_by": holder
            })
        return slots_data

    @staticmethod
    async def hold_slot(db: AsyncSession, slot_id: int, call_id: str, ttl: int = 180) -> Dict[str, Any]:
        """
        Attempts to acquire a 3-minute Redis soft-hold on a specific slot.
        """
        stmt = select(Slot).where(Slot.id == slot_id)
        res = await db.execute(stmt)
        slot = res.scalars().first()
        if not slot:
            return {"success": False, "error": "Slot does not exist."}
        if slot.is_booked:
            return {"success": False, "error": "Slot is already booked."}

        # Check existing hold
        if await redis_service.is_slot_held_by_other(slot_id, call_id):
            return {"success": False, "error": "Slot is currently held by another caller."}

        acquired = await redis_service.acquire_slot_hold(slot_id, call_id, ttl=ttl)
        if not acquired:
            return {"success": False, "error": "Could not acquire soft hold on slot."}

        await audit_service.log_event(
            db=db,
            event_type="SLOT_HOLD_ACQUIRED",
            call_id=call_id,
            payload_data={"slot_id": slot_id, "ttl": ttl}
        )
        await db.commit()

        return {"success": True, "slot_id": slot_id, "ttl": ttl}

    @staticmethod
    async def find_and_hold_next_slot(db: AsyncSession, department: str, call_id: str) -> Optional[Dict[str, Any]]:
        """
        FCFS: Finds earliest unbooked slot for department and attempts atomic hold.
        """
        available_slots = await SchedulingService.get_available_slots(db, department=department)
        for s in available_slots:
            if not s["is_held"]:
                hold_result = await SchedulingService.hold_slot(db, s["slot_id"], call_id)
                if hold_result.get("success"):
                    return s
        return None

    @staticmethod
    async def confirm_booking(
        db: AsyncSession,
        call_id: str,
        slot_id: int,
        patient_name: str,
        patient_age: int,
        caller_phone: str,
        department: str,
        triage_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transactional, Concurrency-Safe Final Booking:
        1. Checks call_id idempotency.
        2. Checks hold validity.
        3. Locks slot row (with_for_update in PostgreSQL / mutex serialization in SQLite).
        4. Verifies slot is not booked.
        5. Atomically increments and assigns daily sequential token.
        6. Persists Appointment and TriageNote.
        7. Releases Redis soft-hold and records SHA-256 hash-chained audit log.
        """
        async with _scheduling_tx_lock:
            # 1. Idempotency Check: if call_id already has an appointment, return it!
            existing_stmt = select(Appointment).where(Appointment.call_id == call_id)
            existing_res = await db.execute(existing_stmt)
            existing_apt = existing_res.scalars().first()
            if existing_apt:
                logger.info("Idempotent request received for call_id: %s. Returning existing token: %s", call_id, existing_apt.token_id)
                return {
                    "success": True,
                    "is_idempotent_replay": True,
                    "token_id": existing_apt.token_id,
                    "department": existing_apt.department,
                    "queue_position": existing_apt.queue_position,
                    "message": "Appointment already booked for this call session."
                }

            # 2. Verify soft hold is not owned by someone else
            if await redis_service.is_slot_held_by_other(slot_id, call_id):
                return {
                    "success": False,
                    "error": "Slot reservation expired or claimed by another caller. Please choose another slot."
                }

            # 3. Lock slot with row-level locking
            try:
                is_sqlite = db.bind.dialect.name == "sqlite" if db.bind else True
                slot_stmt = select(Slot).where(Slot.id == slot_id)
                if not is_sqlite:
                    slot_stmt = slot_stmt.with_for_update()

                slot_res = await db.execute(slot_stmt)
                slot = slot_res.scalars().first()

                if not slot:
                    return {"success": False, "error": "Requested slot not found."}

                if slot.is_booked:
                    await redis_service.release_slot_hold(slot_id, call_id)
                    return {"success": False, "error": "Slot was already booked by another transaction."}

                # Fetch doctor
                doc_stmt = select(Doctor).where(Doctor.id == slot.doctor_id)
                doc_res = await db.execute(doc_stmt)
                doctor = doc_res.scalars().first()
                if not doctor:
                    return {"success": False, "error": "Assigned doctor not found."}

                # 4. Generate sequential atomic token for department and day
                today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
                prefix = SchedulingService.get_department_prefix(department)
                
                # Count appointments today for this department to determine sequence
                try:
                    count_stmt = (
                        select(func.count(Appointment.id))
                        .where(
                            and_(
                                Appointment.department == department,
                                func.strftime('%Y%m%d', Appointment.booked_at) == today_str if is_sqlite
                                else func.to_char(Appointment.booked_at, 'YYYYMMDD') == today_str
                            )
                        )
                    )
                    count_res = await db.execute(count_stmt)
                    dept_today_count = count_res.scalar() or 0
                except Exception:
                    count_res = await db.execute(select(func.count(Appointment.id)).where(Appointment.department == department))
                    dept_today_count = count_res.scalar() or 0

                next_seq = dept_today_count + 1
                token_id = f"{prefix}-{today_str}-{next_seq:03d}"

                # Calculate queue position
                active_q_stmt = select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.doctor_id == doctor.id,
                        Appointment.status.in_(["SCHEDULED", "IN_QUEUE"])
                    )
                )
                q_res = await db.execute(active_q_stmt)
                queue_pos = (q_res.scalar() or 0) + 1

                # Mark slot booked
                slot.is_booked = True

                # Create Appointment
                appointment = Appointment(
                    token_id=token_id,
                    caller_phone=caller_phone,
                    call_id=call_id,
                    patient_name=patient_name,
                    patient_age=patient_age,
                    slot_id=slot.id,
                    doctor_id=doctor.id,
                    department=department,
                    status="SCHEDULED",
                    queue_position=queue_pos,
                    follow_up_status="NOT_TRIGGERED"
                )
                db.add(appointment)
                await db.flush()

                # Create TriageNote if triage_data passed
                if triage_data:
                    triage_note = TriageNote(
                        appointment_id=appointment.id,
                        call_id=call_id,
                        chief_complaint=triage_data.get("chief_complaint", "Not specified"),
                        duration=triage_data.get("duration", "Recent"),
                        severity_scale=int(triage_data.get("severity_scale_1_to_10", 5)),
                        age=patient_age,
                        associated_symptoms=json.dumps(triage_data.get("associated_symptoms", [])),
                        triage_confidence=float(triage_data.get("triage_confidence", 0.9)),
                        chosen_department=department,
                        department_rationale=triage_data.get("department_rationale", "Standard department mapping."),
                        handoff_brief=triage_data.get("handoff_brief", f"Patient {patient_name}, age {patient_age}, booked for {department}."),
                        urgency_level=triage_data.get("urgency_level", "ROUTINE")
                    )
                    db.add(triage_note)

                # Audit log entry for committed booking
                await audit_service.log_event(
                    db=db,
                    event_type="BOOKING_COMMITTED",
                    call_id=call_id,
                    payload_data={
                        "token_id": token_id,
                        "slot_id": slot.id,
                        "doctor_id": doctor.id,
                        "department": department,
                        "patient_name": patient_name,
                        "slot_timestamp": slot.slot_timestamp.isoformat()
                    }
                )

                # Commit transaction atomically
                await db.commit()

                # Release Redis soft hold
                await redis_service.release_slot_hold(slot.id, call_id)

                return {
                    "success": True,
                    "token_id": token_id,
                    "department": department,
                    "doctor_name": doctor.name,
                    "room_number": doctor.room_number,
                    "slot_timestamp": slot.slot_timestamp.isoformat(),
                    "queue_position": queue_pos,
                    "patient_name": patient_name,
                    "appointment_id": appointment.id,
                    "message": f"Appointment confirmed with {doctor.name}. Token: {token_id}."
                }

            except Exception as e:
                await db.rollback()
                logger.error("Booking transaction failed: %s", e, exc_info=True)
                return {"success": False, "error": f"Transaction failed: {str(e)}"}

scheduling_service = SchedulingService()
