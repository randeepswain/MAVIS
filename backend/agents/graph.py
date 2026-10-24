import logging
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from backend.agents.safety_gate import safety_gate
from backend.agents.receptionist import receptionist_agent
from backend.agents.triage_agent import triage_agent
from backend.agents.handoff_agent import handoff_agent

logger = logging.getLogger("mavis.langgraph")

class MavisGraphState(TypedDict):
    call_id: str
    caller_phone: str
    current_utterance: str
    stage: str # 'reception', 'triage', 'clarification', 'booking', 'emergency', 'completed'
    consent_given: bool
    red_flag_triggered: bool
    red_flag_details: Optional[Dict[str, Any]]
    patient_name: str
    patient_age: int
    extracted_symptoms: Optional[Dict[str, Any]]
    target_department: str
    department_confidence: float
    department_rationale: str
    clarification_question: Optional[str]
    slot_id: Optional[int]
    held_slot: Optional[Dict[str, Any]]
    booked_appointment: Optional[Dict[str, Any]]
    handoff_brief: Optional[str]
    system_response: str
    history: List[Dict[str, str]]

# Node 1: Synchronous Rule-Based Safety Gate Node (F4)
async def safety_node(state: MavisGraphState) -> Dict[str, Any]:
    utterance = state.get("current_utterance", "")
    is_red_flag, trigger, rationale = safety_gate.evaluate_utterance(utterance)

    if is_red_flag:
        return {
            "red_flag_triggered": True,
            "stage": "emergency",
            "red_flag_details": {
                "trigger_phrase": trigger,
                "clinical_rationale": rationale
            },
            "system_response": (
                "EMERGENCY RED-FLAG TRIGGERED: Critical symptoms detected. "
                "Immediately terminating scheduling automation. "
                "Initiating live call bridge transfer to a Human Triage Nurse and alerting the hospital emergency response team."
            )
        }
    return {
        "red_flag_triggered": False
    }

# Node 2: Emergency Terminal Node
async def emergency_node(state: MavisGraphState) -> Dict[str, Any]:
    return {
        "stage": "emergency"
    }

# Node 3: Receptionist Node
async def receptionist_node(state: MavisGraphState) -> Dict[str, Any]:
    utterance = state.get("current_utterance", "")
    consent_result = receptionist_agent.process_consent(utterance)
    
    if not consent_result["consent_granted"]:
        return {
            "stage": "completed",
            "consent_given": False,
            "system_response": consent_result["response"]
        }

    return {
        "consent_given": True,
        "stage": "triage",
        "system_response": consent_result["response"]
    }

# Node 4: Symptom Triage Node (F1)
async def triage_node(state: MavisGraphState) -> Dict[str, Any]:
    utterance = state.get("current_utterance", "")
    already_clarified = (state.get("stage") == "clarification")
    prior_complaint = None
    if already_clarified and state.get("extracted_symptoms"):
        prior_complaint = state["extracted_symptoms"].get("chief_complaint")
    
    triage_result = await triage_agent.triage_and_route(
        utterance=utterance,
        already_clarified=already_clarified,
        prior_complaint=prior_complaint
    )

    if triage_result.get("needs_clarification"):
        clarification_q = triage_result.get("clarifying_question") or triage_result.get("clarification_question", "Could you describe your symptoms in more detail?")
        return {
            "stage": "clarification",
            "clarification_question": clarification_q,
            "target_department": triage_result.get("tentative_department", "General Medicine"),
            "department_confidence": triage_result.get("confidence", 0.5),
            "extracted_symptoms": triage_result.get("extracted_data"),
            "system_response": triage_result.get("system_response", clarification_q)
        }

    extracted = triage_result.get("extracted_data", {})
    return {
        "stage": "booking",
        "target_department": triage_result.get("target_department", state.get("target_department", "General Medicine")),
        "department_confidence": triage_result.get("confidence", 0.8),
        "department_rationale": triage_result.get("department_rationale", "Routine triage assignment."),
        "extracted_symptoms": extracted,
        "patient_name": extracted.get("patient_name", state.get("patient_name", "Patient")),
        "patient_age": extracted.get("age", state.get("patient_age", 35)),
        "system_response": triage_result.get("system_response", "Assigning consultation slot.")
    }

# Router logic
def route_after_safety(state: MavisGraphState) -> str:
    if state.get("red_flag_triggered"):
        return "emergency"
    stage = state.get("stage", "reception")
    if stage == "reception":
        return "receptionist"
    elif stage in ["triage", "clarification"]:
        return "triage"
    return "receptionist"

def build_mavis_graph():
    workflow = StateGraph(MavisGraphState)

    workflow.add_node("safety_gate", safety_node)
    workflow.add_node("emergency", emergency_node)
    workflow.add_node("receptionist", receptionist_node)
    workflow.add_node("triage", triage_node)

    workflow.set_entry_point("safety_gate")

    workflow.add_conditional_edges(
        "safety_gate",
        route_after_safety,
        {
            "emergency": "emergency",
            "receptionist": "receptionist",
            "triage": "triage"
        }
    )

    workflow.add_edge("emergency", END)
    workflow.add_edge("receptionist", END)
    workflow.add_edge("triage", END)

    return workflow.compile()

mavis_orchestrator = build_mavis_graph()
