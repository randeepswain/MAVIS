import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import datetime
import pytest
from sqlalchemy import select
from backend.database.session import AsyncSessionLocal, init_db
from backend.database.models import Doctor, Slot, Appointment
from backend.services.scheduling import scheduling_service
from backend.services.redis_service import redis_service

@pytest.mark.asyncio
async def test_concurrent_slot_bookings_zero_double_bookings():
    """
    Simulates high concurrency: 100 concurrent callers all attempting to book 
    the EXACT SAME physical slot at the exact same millisecond.
    Guarantees:
    - Exactly 1 caller succeeds in booking the slot.
    - 99 callers are safely rejected.
    - Zero double bookings occur in the database!
    """
    await init_db()
    await redis_service.initialize()

    # Create a fresh doctor and a single target slot for this test
    async with AsyncSessionLocal() as session:
        doc = Doctor(
            name="Dr. Concurrency Test",
            department="Cardiology",
            specialization="Stress Testing",
            room_number="TEST-999"
        )
        session.add(doc)
        await session.flush()

        test_slot = Slot(
            doctor_id=doc.id,
            slot_timestamp=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2),
            is_booked=False
        )
        session.add(test_slot)
        await session.commit()
        target_slot_id = test_slot.id

    # Launch 100 concurrent booking requests
    num_concurrent_requests = 100
    
    async def attempt_booking(caller_idx: int):
        call_id = f"stress-call-{caller_idx}-{int(datetime.datetime.now().timestamp()*1000)}"
        async with AsyncSessionLocal() as session:
            # Hold then confirm
            hold = await scheduling_service.hold_slot(session, target_slot_id, call_id=call_id)
            if not hold.get("success"):
                return {"caller_idx": caller_idx, "success": False, "stage": "hold_rejected"}

            res = await scheduling_service.confirm_booking(
                db=session,
                call_id=call_id,
                slot_id=target_slot_id,
                patient_name=f"Patient {caller_idx}",
                patient_age=30 + (caller_idx % 40),
                caller_phone=f"+91-90000-{caller_idx:05d}",
                department="Cardiology"
            )
            return {"caller_idx": caller_idx, "success": res.get("success", False), "result": res}

    tasks = [attempt_booking(i) for i in range(num_concurrent_requests)]
    results = await asyncio.gather(*tasks)

    successful = [r for r in results if r.get("success") is True]
    rejected = [r for r in results if r.get("success") is False]

    print(f"\n[CONCURRENCY TEST] 100 Concurrent Callers -> Successful: {len(successful)}, Rejected: {len(rejected)}")

    # Strict Assertion: EXACTLY 1 booking succeeded
    assert len(successful) == 1, f"Expected exactly 1 successful booking, but got {len(successful)}"
    assert len(rejected) == num_concurrent_requests - 1

    # Verify database state
    async with AsyncSessionLocal() as session:
        slot_check = (await session.execute(select(Slot).where(Slot.id == target_slot_id))).scalars().first()
        assert slot_check.is_booked is True

        appointments = (await session.execute(select(Appointment).where(Appointment.slot_id == target_slot_id))).scalars().all()
        assert len(appointments) == 1, "CRITICAL: Double booking detected in DB!"

@pytest.mark.asyncio
async def test_idempotency_on_dropped_call_reconnect():
    """
    Verifies that if a caller network drops or reconnects and retries with the SAME call_id,
    the system does NOT create a second booking or error out, but returns the existing token!
    """
    await init_db()
    async with AsyncSessionLocal() as session:
        # Create a test slot
        doc = (await session.execute(select(Doctor))).scalars().first()
        slot = Slot(
            doctor_id=doc.id,
            slot_timestamp=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5),
            is_booked=False
        )
        session.add(slot)
        await session.commit()
        slot_id = slot.id

    call_id = "dropped-network-call-999"

    # Request 1
    async with AsyncSessionLocal() as session:
        res1 = await scheduling_service.confirm_booking(
            db=session,
            call_id=call_id,
            slot_id=slot_id,
            patient_name="Suresh Kumar",
            patient_age=45,
            caller_phone="+91-98765-43210",
            department="Cardiology"
        )
        assert res1["success"] is True
        token1 = res1["token_id"]

    # Request 2 (Identical call_id retransmitted)
    async with AsyncSessionLocal() as session:
        res2 = await scheduling_service.confirm_booking(
            db=session,
            call_id=call_id,
            slot_id=slot_id,
            patient_name="Suresh Kumar",
            patient_age=45,
            caller_phone="+91-98765-43210",
            department="Cardiology"
        )
        assert res2["success"] is True
        assert res2["token_id"] == token1
        assert res2.get("is_idempotent_replay") is True

    print(f"\n[IDEMPOTENCY TEST] Reconnection with call_id '{call_id}' safely returned token '{token1}'.")

if __name__ == "__main__":
    asyncio.run(test_concurrent_slot_bookings_zero_double_bookings())
    asyncio.run(test_idempotency_on_dropped_call_reconnect())
    print("All Concurrency & Idempotency tests passed with ZERO double bookings!")
