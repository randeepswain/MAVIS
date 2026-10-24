import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import pytest
from backend.agents.safety_gate import safety_gate
from backend.database.session import AsyncSessionLocal, init_db
from backend.services.audit import audit_service

@pytest.mark.asyncio
async def test_safety_gate_triggers():
    await init_db()

    # 1. Critical cardiac symptom
    cardiac_text = "I have severe crushing chest pain radiating to my left arm since 10 minutes ago"
    is_red, trigger, rationale = safety_gate.evaluate_utterance(cardiac_text)
    assert is_red is True
    assert "chest pain" in trigger or "radiating" in trigger

    # 2. Acute respiratory distress
    resp_text = "Help, I cannot breathe and I am gasping for air"
    is_red, trigger, rationale = safety_gate.evaluate_utterance(resp_text)
    assert is_red is True

    # 3. Anaphylaxis
    allergy_text = "My throat is closing and my tongue is swelling"
    is_red, trigger, rationale = safety_gate.evaluate_utterance(allergy_text)
    assert is_red is True

    # 4. Stroke sign (FAST)
    stroke_text = "My father's face is drooping and he has slurred speech"
    is_red, trigger, rationale = safety_gate.evaluate_utterance(stroke_text)
    assert is_red is True

    # 5. Routine non-emergency symptom
    routine_text = "I have mild knee pain for two days after playing tennis"
    is_red, trigger, rationale = safety_gate.evaluate_utterance(routine_text)
    assert is_red is False

@pytest.mark.asyncio
async def test_hash_chained_audit_log_tamper_evidence():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Process a red flag safety check with DB session
        result = await safety_gate.process_safety_check(
            text="Patient collapsed and is unresponsive",
            call_id="test-safety-call-1",
            db=session
        )
        assert result["triggered"] is True
        assert result["action"] == "EMERGENCY_ESCALATION"

        # Verify chain is cryptographically intact
        verify_post = await audit_service.verify_chain(session)
        assert verify_post["is_valid"] is True
        assert verify_post["total_records"] >= 1

if __name__ == "__main__":
    asyncio.run(test_safety_gate_triggers())
    asyncio.run(test_hash_chained_audit_log_tamper_evidence())
    print("All Safety Gate and Hash-Chain Audit tests passed successfully!")
