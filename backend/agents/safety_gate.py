import re
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.audit import audit_service
from backend.config import settings

# Comprehensive clinical regex patterns for emergency red-flag indicators
RED_FLAG_PATTERNS = [
    # Cardiac / Coronary syndrome
    (r"\b(crushing|severe|radiating|intense|squeezing)\s+(chest\s+pain|chest\s+pressure|heart\s+pain)\b", "Severe acute coronary syndrome risk / chest pain"),
    (r"\bpain\s+(radiating|spreading)\s+to\s+(my\s+)?(left\s+arm|jaw|neck|back)\b", "Angina radiation to left arm or jaw"),
    (r"\b(heart\s+attack|myocardial\s+infarction)\b", "Suspected acute myocardial infarction"),
    
    # Severe Respiratory Distress / Airway Obstruction
    (r"\b(cannot|can't|unable\s+to)\s+breathe\b", "Acute respiratory failure"),
    (r"\b(gasping\s+for\s+air|suffocating|choking|turning\s+blue|cyanosis)\b", "Severe respiratory distress / acute airway compromise"),
    (r"\b(throat|tongue|lips|airway)\s+(is\s+)?(closing|swelling|swollen)\b", "Anaphylactic shock / acute upper airway angioedema"),
    (r"\b(swelling|swollen)\s+(of\s+)?(my\s+)?(tongue|throat|lips)\b", "Anaphylactic shock / angioedema"),
    (r"\b(anaphylaxis|severe\s+allergic\s+reaction)\b", "Anaphylaxis warning"),
    
    # Cerebrovascular / Neurological Emergency (FAST criteria)
    (r"\b(face\s+drooping|facial\s+droop|slurred\s+speech|can't\s+speak|unable\s+to\s+talk)\b", "Acute stroke / cerebrovascular event (FAST)"),
    (r"\b(one[\s-]sided\s+(weakness|paralysis|numbness)|sudden\s+paralysis)\b", "Acute hemiparesis / stroke warning"),
    (r"\b(passed\s+out|collapsed|unresponsive|loss\s+of\s+consciousness|blacked\s+out)\b", "Syncope / sudden loss of consciousness"),
    (r"\b(ongoing\s+seizure|active\s+convulsion|epileptic\s+fit)\b", "Active seizure / status epilepticus risk"),

    # Hemorrhage / Trauma
    (r"\b(uncontrolled\s+bleeding|gushing\s+blood|spurting\s+blood|bleeding\s+heavily)\b", "Severe uncontained hemorrhage"),
    (r"\b(coughing\s+up\s+blood|vomiting\s+(large\s+amounts?\s+of\s+)?blood)\b", "Massive hemoptysis or hematemesis"),
    
    # Poisoning / Crisis
    (r"\b(overdose|swallowed\s+poison|took\s+too\s+many\s+pills)\b", "Acute toxicity / drug overdose"),
    (r"\b(want\s+to\s+(kill|end)\s+myself|suicide)\b", "Acute psychiatric crisis / self-harm")
]

class SafetyGate:
    """
    Emergency Red-Flag Safety Gate (F4).
    Runs synchronously and deterministically on EVERY caller utterance BEFORE LLM processing.
    """
    @classmethod
    def evaluate_utterance(cls, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Returns: (is_red_flag: bool, matched_pattern: str, clinical_rationale: str)
        """
        clean_text = text.strip().lower()
        if not clean_text:
            return False, None, None

        for pattern, rationale in RED_FLAG_PATTERNS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return True, match.group(0), rationale

        return False, None, None

    @classmethod
    async def process_safety_check(
        cls,
        text: str,
        call_id: str,
        db: Optional[AsyncSession] = None,
        caller_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes zero-tolerance check and automatically records SHA-256 hash-chained audit log
        if red flag is detected.
        """
        is_red_flag, trigger_word, rationale = cls.evaluate_utterance(text)

        if not is_red_flag:
            return {
                "triggered": False,
                "action": "PROCEED_TO_AGENTS"
            }

        # RED FLAG TRIGGERED! Immediate bypass
        escalation_payload = {
            "trigger_phrase": trigger_word,
            "clinical_rationale": rationale,
            "caller_phone": caller_phone or "UNKNOWN",
            "transferred_to_desk": settings.EMERGENCY_DESK_PHONE,
            "fallback_emergency_lines": [settings.EMERGENCY_FALLBACK_1, settings.EMERGENCY_FALLBACK_2],
            "action_taken": "SCHEDULING_TERMINATED_INSTANT_CALL_BRIDGE"
        }

        audit_entry_id = None
        record_hash = None
        if db:
            audit_log = await audit_service.log_event(
                db=db,
                event_type="EMERGENCY_RED_FLAG_TRIGGERED",
                payload_data=escalation_payload,
                call_id=call_id
            )
            await db.commit()
            audit_entry_id = audit_log.id
            record_hash = audit_log.record_hash

        return {
            "triggered": True,
            "action": "EMERGENCY_ESCALATION",
            "trigger_phrase": trigger_word,
            "clinical_rationale": rationale,
            "audit_entry_id": audit_entry_id,
            "record_hash": record_hash,
            "call_bridge_info": {
                "transfer_target": "Human Triage Nurse / On-Call Physician",
                "phone_number": settings.EMERGENCY_DESK_PHONE,
                "emergency_fallbacks": ["112 (National Emergency)", "108 (Ambulance)"]
            },
            "system_speech": (
                "EMERGENCY ALERT: Your symptoms indicate an urgent medical situation. "
                "I am immediately transferring your call to a Human Triage Nurse and alerting the emergency medical team. "
                "Please stay on the line, or dial 112 or 108 immediately if the call drops."
            )
        }

safety_gate = SafetyGate()
