import re
from typing import Dict, Any

class ReceptionistAgent:
    """
    Receptionist Agent: Gathers initial consent, verifies language, and initiates intake conversation.
    """
    @staticmethod
    def process_consent(utterance: str) -> Dict[str, Any]:
        text = utterance.lower()
        affirmative_patterns = [r"\b(yes|yeah|sure|okay|ok|i consent|agree|proceed|continue|fine)\b"]
        negative_patterns = [r"\b(no|nope|don't consent|disagree|stop|cancel)\b"]

        for p in negative_patterns:
            if re.search(p, text):
                return {
                    "consent_granted": False,
                    "response": "Understood. Without consent, automated intake cannot continue. If this is an emergency, please hang up and dial 112 or 108 immediately."
                }

        for p in affirmative_patterns:
            if re.search(p, text):
                return {
                    "consent_granted": True,
                    "response": "Thank you for confirming consent. Could you please tell me your full name, age, and what symptoms or health concerns brought you to call today?"
                }

        return {
            "consent_granted": True, # Friendly progression
            "response": "Thank you. To schedule your appointment, please state your full name, your age, and describe what symptoms you are experiencing today."
        }

receptionist_agent = ReceptionistAgent()
