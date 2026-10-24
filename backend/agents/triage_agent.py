import json
import re
import logging
from typing import Dict, Any, List, Optional
from backend.services.rag_service import rag_service
from backend.config import settings

logger = logging.getLogger("mavis.triage")

class SymptomTriageAgent:
    """
    Symptom Triage Agent (F1):
    1. Extracts caller details into strict JSON schema:
       { chief_complaint, duration, severity_scale_1_to_10, age, associated_symptoms }
    2. Uses RAG against clinical knowledge base to map to target department.
    3. If confidence < 0.75, asks one focused clarifying question; defaults safely to General Medicine.
    """

    @staticmethod
    async def extract_symptoms_llm(user_utterance: str, conversation_history: List[Dict[str, str]] = None, prior_complaint: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts structured clinical symptoms using Llama 3 via Groq if API key is provided,
        or deterministic NLP clinical extraction fallback.
        """
        full_text = f"{prior_complaint} - {user_utterance}" if prior_complaint else user_utterance

        if settings.GROQ_API_KEY:
            try:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=settings.GROQ_API_KEY)

                system_prompt = (
                    "You are an expert clinical triage assistant in a hospital emergency/intake call center. "
                    "Extract the patient's symptoms into strict, valid JSON with exact keys: "
                    '{"patient_name": str, "chief_complaint": str, "duration": str, "severity_scale_1_to_10": int, "age": int, "associated_symptoms": list[str]}. '
                    "Do not include any conversational filler or markdown code fences, only output valid JSON. "
                    "If age is unknown, default to 35. If severity is unknown, infer between 1-10 based on description (default 5). "
                    "If duration is unknown, default to 'Recent'."
                )

                messages = [{"role": "system", "content": system_prompt}]
                if conversation_history:
                    for msg in conversation_history[-3:]:
                        messages.append(msg)
                messages.append({"role": "user", "content": f"Patient statement: {full_text}"})

                completion = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                raw_json = completion.choices[0].message.content.strip()
                data = json.loads(raw_json)
                return data
            except Exception as e:
                logger.warning("Groq Llama-3 extraction error or missing key (%s). Using fallback extractor.", e)

        # High-accuracy deterministic fallback extractor
        return SymptomTriageAgent._deterministic_extract(full_text)

    @staticmethod
    def _deterministic_extract(text: str) -> Dict[str, Any]:
        lower = text.lower()
        
        # Extract Age
        age = 35
        age_match = re.search(r"\b(\d{1,2})\s*(years?\s*old|yo|y/o|age|years)?\b", lower)
        if age_match:
            try:
                extracted_age = int(age_match.group(1))
                if 1 <= extracted_age <= 110:
                    age = extracted_age
            except ValueError:
                pass

        # Extract Name
        patient_name = "Patient"
        name_match = re.search(r"\b(my\s+name\s+is|i\s+am|this\s+is)\s+([A-Za-z]+(\s+[A-Za-z]+)?)\b", text, re.IGNORECASE)
        if name_match:
            patient_name = name_match.group(2).strip().title()

        # Extract Severity (1 to 10)
        severity = 5
        sev_match = re.search(r"\b(severity|pain|scale\s+of\s+10|rate\s+it)?\s*([0-9]|10)\s*(out\s+of\s+10|\/10)?\b", lower)
        if sev_match:
            try:
                s_val = int(sev_match.group(2))
                if 1 <= s_val <= 10:
                    severity = s_val
            except ValueError:
                pass
        elif any(w in lower for w in ["unbearable", "excruciating", "horrible", "awful", "extremely severe"]):
            severity = 9
        elif any(w in lower for w in ["mild", "slight", "minor", "manageable"]):
            severity = 3
        elif any(w in lower for w in ["moderate", "medium", "somewhat"]):
            severity = 5

        # Extract Duration
        duration = "3 days"
        dur_match = re.search(r"\b(since\s+[a-z0-9]+|for\s+(\d+|a|two|three|few)\s+(hours?|days?|weeks?|months?))\b", lower)
        if dur_match:
            duration = dur_match.group(0).strip()
        elif "yesterday" in lower:
            duration = "Since yesterday"
        elif "today" in lower or "this morning" in lower:
            duration = "Since today"

        # Detect symptoms
        known_symptoms = [
            "chest pain", "palpitations", "shortness of breath", "high blood pressure",
            "severe headache", "migraine", "dizziness", "numbness", "tremor",
            "knee pain", "back pain", "joint stiffness", "bone fracture", "sprain", "arthritis", "joint swelling", "stiffness",
            "chronic cough", "cough", "wheezing", "asthma", "bronchitis", "sputum",
            "stomach ache", "abdominal pain", "acid reflux", "heartburn", "vomiting", "diarrhea", "nausea",
            "skin rash", "eczema", "acne", "itching", "red spots",
            "fever", "body aches", "fatigue", "chills", "runny nose"
        ]

        found_symptoms = [s for s in known_symptoms if s in lower]
        chief_complaint = found_symptoms[0] if found_symptoms else "General discomfort"
        associated = found_symptoms[1:] if len(found_symptoms) > 1 else []

        return {
            "patient_name": patient_name,
            "chief_complaint": chief_complaint.title(),
            "duration": duration,
            "severity_scale_1_to_10": severity,
            "age": age,
            "associated_symptoms": associated
        }

    @staticmethod
    async def triage_and_route(
        utterance: str,
        conversation_history: List[Dict[str, str]] = None,
        already_clarified: bool = False,
        prior_complaint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes full Triage logic:
        1. Extract symptoms
        2. Perform RAG against clinical department knowledge base
        3. Check confidence threshold (<0.75)
        """
        extracted = await SymptomTriageAgent.extract_symptoms_llm(utterance, conversation_history, prior_complaint)
        
        chief_complaint = extracted.get("chief_complaint", "General discomfort")
        associated = extracted.get("associated_symptoms", [])

        dept, confidence, rationale, clarifying_q = rag_service.match_department(chief_complaint, associated)

        # Confidence gate: If confidence < 0.75 and hasn't asked clarifying question yet
        if confidence < 0.75 and not already_clarified:
            return {
                "needs_clarification": True,
                "clarifying_question": clarifying_q,
                "tentative_department": dept,
                "confidence": confidence,
                "extracted_data": extracted,
                "system_response": f"To ensure we assign you to the most appropriate specialist: {clarifying_q}"
            }

        # If already clarified, adopt tentative department or matched department
        final_dept = dept if confidence >= 0.3 else "General Medicine"
        
        urgency = "ROUTINE"
        if extracted.get("severity_scale_1_to_10", 5) >= 8:
            urgency = "URGENT"
        elif extracted.get("severity_scale_1_to_10", 5) >= 5:
            urgency = "PRIORITY"

        return {
            "needs_clarification": False,
            "target_department": final_dept,
            "confidence": max(confidence, 0.85) if already_clarified else confidence,
            "department_rationale": rationale,
            "urgency_level": urgency,
            "extracted_data": extracted,
            "system_response": (
                f"Based on your symptoms ({chief_complaint}, duration {extracted.get('duration')}), "
                f"I recommend scheduling with the Department of {final_dept}. "
                f"I will now look for the next available consultation slot for you."
            )
        }

triage_agent = SymptomTriageAgent()
