import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import pytest
from backend.agents.graph import mavis_orchestrator
from backend.agents.triage_agent import triage_agent
from backend.agents.handoff_agent import handoff_agent

@pytest.mark.asyncio
async def test_multi_agent_graph_transitions():
    # 1. Reception Stage
    state_init = {
        "call_id": "test-call-100",
        "caller_phone": "+91-98765-11111",
        "current_utterance": "Yes, I consent to proceed with intake",
        "stage": "reception",
        "consent_given": False,
        "red_flag_triggered": False,
        "red_flag_details": None,
        "patient_name": "Test Patient",
        "patient_age": 35,
        "extracted_symptoms": None,
        "target_department": "",
        "department_confidence": 0.0,
        "department_rationale": "",
        "clarification_question": None,
        "slot_id": None,
        "held_slot": None,
        "booked_appointment": None,
        "handoff_brief": None,
        "system_response": "",
        "history": []
    }

    res1 = await mavis_orchestrator.ainvoke(state_init)
    assert res1["consent_given"] is True
    assert res1["stage"] == "triage"
    print("\n[AGENT TEST] Receptionist passed consent, transitioned to 'triage'")

    # 2. Triage Stage with Specific Symptoms:
    # First utterance triggers focused clarifying question if confidence < 0.75
    state_triage = {
        **res1,
        "current_utterance": "My name is Rajesh, 42 years old. I have knee pain for 3 days after football."
    }
    res2 = await mavis_orchestrator.ainvoke(state_triage)
    print(f"[AGENT TEST] Initial triage stage: {res2['stage']}, confidence: {res2.get('department_confidence')}")
    
    # 3. Patient answers clarifying question -> transitions to booking
    state_clarified = {
        **res2,
        "current_utterance": "Yes, it happened during a tackle and I have joint swelling, bone stiffness, and cannot bend the knee."
    }
    res3 = await mavis_orchestrator.ainvoke(state_clarified)
    assert res3["target_department"] == "Orthopedics"
    assert res3["stage"] == "booking"
    print(f"[AGENT TEST] After clarification, mapped to '{res3['target_department']}' with stage '{res3['stage']}'")

    # 4. Emergency Bypass via Multi-Agent Graph
    state_emergency = {
        **res1,
        "current_utterance": "Help, my chest pain is crushing and spreading to my left arm, I can't breathe"
    }
    res_emrg = await mavis_orchestrator.ainvoke(state_emergency)
    assert res_emrg["red_flag_triggered"] is True
    assert res_emrg["stage"] == "emergency"
    assert "EMERGENCY" in res_emrg["system_response"]
    print("[AGENT TEST] Red-flag emergency utterance instantly bypassed to emergency node")

@pytest.mark.asyncio
async def test_clarification_and_handoff_brief():
    # Ambiguous symptom
    res = await triage_agent.triage_and_route("I feel a little strange and tired", already_clarified=False)
    if res.get("needs_clarification"):
        assert "clarifying_question" in res or "clarification_question" in res
        print("[AGENT TEST] Low-confidence triggered clarifying question as required.")

    # Handoff Brief test
    brief = handoff_agent.generate_brief(
        token_id="CARD-20261020-001",
        patient_name="Aarav Mehta",
        patient_age=48,
        department="Cardiology",
        doctor_name="Dr. Priya Sharma",
        slot_timestamp="2026-10-20 14:00",
        chief_complaint="Chest tightness on stairs",
        duration="4 days",
        severity=6,
        associated_symptoms=["shortness of breath", "fatigue"],
        triage_confidence=0.92,
        department_rationale="Coronary evaluation needed",
        urgency_level="URGENT"
    )
    assert "CARD-20261020-001" in brief
    assert "CLINICAL HANDOFF BRIEF" in brief
    assert "12-lead ECG" in brief
    print("[AGENT TEST] Structured Clinical Handoff Brief verified successfully.")

if __name__ == "__main__":
    asyncio.run(test_multi_agent_graph_transitions())
    asyncio.run(test_clarification_and_handoff_brief())
    print("All Multi-Agent LangGraph tests passed successfully!")
