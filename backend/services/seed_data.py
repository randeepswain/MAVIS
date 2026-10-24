import datetime
import hashlib
import json
import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.models import User, Doctor, Slot, Appointment, TriageNote, AuditLog, FollowUpRecord
from backend.services.audit import audit_service

logger = logging.getLogger("mavis.seed")

# Simple, reliable password hashing (SHA-256 with salt)
def hash_password(password: str) -> str:
    salt = "mavis_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

async def seed_database(db: AsyncSession):
    """
    Populates standard departments, doctor accounts, shift slots, and initial telemetry data idempotently.
    """
    # 1. Admin User
    admin_check = await db.execute(select(User).where(User.email == "admin@mavis.hospital"))
    admin_user = admin_check.scalars().first()
    if not admin_user:
        admin_user = User(
            email="admin@mavis.hospital",
            hashed_password=hash_password("admin123"),
            full_name="Hospital Director (Admin)",
            role="ADMIN",
            is_active=True
        )
        db.add(admin_user)
        await db.flush()

    # 2. Doctor Users & Doctor Records: Exactly 6 Doctors
    # Dr. A (Ophthalmology), Dr. B (Cardiology), Dr. C (Dermatology), Dr. D (Orthopedics), Dr. E (ENT), Dr. F (General Medicine)
    doctors_info = [
        {"name": "Dr. A", "email": "dr.a@mavis.hospital", "dept": "Ophthalmology", "spec": "Ophthalmology & Refractive Surgery", "room": "OPD-101"},
        {"name": "Dr. B", "email": "dr.b@mavis.hospital", "dept": "Cardiology", "spec": "Interventional Cardiology", "room": "OPD-102"},
        {"name": "Dr. C", "email": "dr.c@mavis.hospital", "dept": "Dermatology", "spec": "Clinical & Cosmetic Dermatology", "room": "OPD-103"},
        {"name": "Dr. D", "email": "dr.d@mavis.hospital", "dept": "Orthopedics", "spec": "Joint Reconstruction & Trauma", "room": "OPD-104"},
        {"name": "Dr. E", "email": "dr.e@mavis.hospital", "dept": "ENT", "spec": "Otorhinolaryngology & Sinus Care", "room": "OPD-105"},
        {"name": "Dr. F", "email": "dr.f@mavis.hospital", "dept": "General Medicine", "spec": "Internal & General Medicine", "room": "OPD-106"},
    ]

    target_names = {d["name"] for d in doctors_info}
    existing_docs = (await db.execute(select(Doctor))).scalars().all()
    if any(doc.name not in target_names for doc in existing_docs) or len(existing_docs) != len(target_names):
        logger.info("Purging legacy doctors and resetting to exactly 6 doctors (Dr. A-E + Dr. F)...")
        await db.execute(delete(FollowUpRecord))
        await db.execute(delete(TriageNote))
        await db.execute(delete(Appointment))
        await db.execute(delete(Slot))
        await db.execute(delete(Doctor))
        await db.execute(delete(User).where(User.role == "DOCTOR"))
        await db.flush()

    doctor_entities = []
    for doc in doctors_info:
        user_check = await db.execute(select(User).where(User.email == doc["email"]))
        user = user_check.scalars().first()
        if not user:
            user = User(
                email=doc["email"],
                hashed_password=hash_password("doctor123"),
                full_name=doc["name"],
                role="DOCTOR",
                is_active=True
            )
            db.add(user)
            await db.flush()

        doc_check = await db.execute(select(Doctor).where(Doctor.name == doc["name"]))
        doctor = doc_check.scalars().first()
        if not doctor:
            doctor = Doctor(
                user_id=user.id,
                name=doc["name"],
                department=doc["dept"],
                specialization=doc["spec"],
                room_number=doc["room"],
                is_active=True
            )
            db.add(doctor)
            await db.flush()

        doctor_entities.append(doctor)

    # 3. Create Slots for each Doctor (Today and Tomorrow)
    now = datetime.datetime.now(datetime.timezone.utc)
    base_date = now.replace(minute=0, second=0, microsecond=0)

    all_slots = []
    slot_hours = [9, 10, 11, 12, 14, 15, 16, 17]
    for doctor in doctor_entities:
        for day_offset in [0, 1]:
            target_date = base_date + datetime.timedelta(days=day_offset)
            for hour in slot_hours:
                slot_time = target_date.replace(hour=hour, minute=0)
                slot_check = await db.execute(
                    select(Slot).where(Slot.doctor_id == doctor.id, Slot.slot_timestamp == slot_time)
                )
                slot = slot_check.scalars().first()
                if not slot:
                    slot = Slot(
                        doctor_id=doctor.id,
                        slot_timestamp=slot_time,
                        is_booked=False
                    )
                    db.add(slot)
                all_slots.append((slot, doctor))

    await db.flush()

    # 4. Create Initial Seed Appointments
    seed_patients = [
        {
            "name": "Aarav Mehta",
            "age": 48,
            "phone": "+91-98765-43210",
            "complaint": "Persistent high blood pressure and chest tightness on stairs",
            "dept": "Cardiology",
            "severity": 6,
            "doctor": doctor_entities[1], # Dr. B (Cardiology)
            "brief": "### CLINICAL HANDOFF BRIEF\n**Token ID:** `CARD-20261020-001` | **Urgency:** `URGENT`\n**Patient:** Aarav Mehta (Age: 48)\n- **Chief Complaint:** Chest tightness on stairs\n- **Duration:** 4 days\n- **Triage Reasoning:** Cardiovascular exertion symptom.\n- **Recommended Initial Workup:** 12-lead ECG, blood pressure series, troponin test."
        },
        {
            "name": "Meera Sen",
            "age": 34,
            "phone": "+91-91234-56789",
            "complaint": "Blurred vision with eye strain and floaters for 3 days",
            "dept": "Ophthalmology",
            "severity": 6,
            "doctor": doctor_entities[0], # Dr. A (Ophthalmology)
            "brief": "### CLINICAL HANDOFF BRIEF\n**Token ID:** `OPHT-20261020-001` | **Urgency:** `URGENT`\n**Patient:** Meera Sen (Age: 34)\n- **Chief Complaint:** Blurred vision with floaters\n- **Duration:** 3 days\n- **Triage Reasoning:** Visual acuity and retinal examination indicated."
        },
        {
            "name": "Rohan Gupta",
            "age": 29,
            "phone": "+91-98888-11111",
            "complaint": "Right knee twisting injury while playing soccer",
            "dept": "Orthopedics",
            "severity": 5,
            "doctor": doctor_entities[3], # Dr. D (Orthopedics)
            "brief": "### CLINICAL HANDOFF BRIEF\n**Token ID:** `ORTH-20261020-001` | **Urgency:** `ROUTINE`\n**Patient:** Rohan Gupta (Age: 29)\n- **Chief Complaint:** Knee swelling and pain after sports\n- **Duration:** 1 day\n- **Triage Reasoning:** Possible meniscus/ACL sprain."
        }
    ]

    for idx, sp in enumerate(seed_patients):
        call_id = f"seed-call-{idx+1}"
        apt_check = await db.execute(select(Appointment).where(Appointment.call_id == call_id))
        if apt_check.scalars().first():
            continue

        doc_slots = [s for s, d in all_slots if d.id == sp["doctor"].id and not s.is_booked]
        if doc_slots:
            target_slot = doc_slots[0]
            target_slot.is_booked = True
            today_str = now.strftime("%Y%m%d")
            dept_code = sp["dept"][:4].upper()
            token_id = f"{dept_code}-{today_str}-{idx+1:03d}"

            # Verify token_id not in DB
            token_check = await db.execute(select(Appointment).where(Appointment.token_id == token_id))
            if token_check.scalars().first():
                token_id = f"{dept_code}-{today_str}-99{idx+1}"

            apt = Appointment(
                token_id=token_id,
                caller_phone=sp["phone"],
                call_id=call_id,
                patient_name=sp["name"],
                patient_age=sp["age"],
                slot_id=target_slot.id,
                doctor_id=sp["doctor"].id,
                department=sp["dept"],
                status="IN_QUEUE" if idx == 0 else "SCHEDULED",
                queue_position=idx + 1,
                follow_up_status="CALLED_RECOVERING" if idx == 2 else "PENDING"
            )
            db.add(apt)
            await db.flush()

            triage = TriageNote(
                appointment_id=apt.id,
                call_id=call_id,
                chief_complaint=sp["complaint"],
                duration="2-4 days",
                severity_scale=sp["severity"],
                age=sp["age"],
                associated_symptoms=json.dumps(["fatigue", "discomfort"]),
                triage_confidence=0.92,
                chosen_department=sp["dept"],
                department_rationale=f"High semantic correlation with {sp['dept']} protocol.",
                handoff_brief=sp["brief"],
                urgency_level="URGENT" if sp["severity"] >= 6 else "ROUTINE"
            )
            db.add(triage)

            if idx == 2:
                fu = FollowUpRecord(
                    appointment_id=apt.id,
                    call_id=call_id,
                    scheduled_at=now,
                    executed_at=now,
                    patient_feedback="Knee pain is reducing with cold compress and rest. Feeling much better.",
                    recovery_condition="IMPROVING",
                    escalated_to_doctor=False
                )
                db.add(fu)

    # 5. Check if audit logs exist
    audit_check = await db.execute(select(AuditLog).limit(1))
    if not audit_check.scalars().first():
        await audit_service.log_event(
            db=db,
            event_type="SYSTEM_INITIALIZED",
            payload_data={"version": "1.0.0", "status": "ALL_SERVICES_ONLINE"},
            call_id="SYSTEM"
        )
        await audit_service.log_event(
            db=db,
            event_type="EMERGENCY_RED_FLAG_TRIGGERED",
            payload_data={
                "trigger_phrase": "crushing chest pain radiating to left arm",
                "clinical_rationale": "Severe acute coronary syndrome risk / chest pain",
                "caller_phone": "+91-99999-00000",
                "transferred_to_desk": "+91-80-2360-1234",
                "fallback_emergency_lines": ["112", "108"],
                "action_taken": "SCHEDULING_TERMINATED_INSTANT_CALL_BRIDGE"
            },
            call_id="emergency-seed-001"
        )

    await db.commit()
    logger.info("Seed database execution complete.")
