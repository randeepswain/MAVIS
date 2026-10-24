from typing import Dict, Any

CLINICAL_WORKUP_SUGGESTIONS = {
    "Cardiology": "12-lead ECG, blood pressure monitoring, serum troponin/lipid profile if indicated, auscultation for murmurs/rubs.",
    "Neurology": "Cranial nerve examination, bilateral reflex testing, Romberg balance test, neuro-vascular screening.",
    "Orthopedics": "Range of motion (ROM) assessment, targeted X-ray/radiograph, weight-bearing tolerance test, joint effusion check.",
    "Pulmonology": "Peak flow spirometry, pulse oximetry (SpO2), chest auscultation for wheezing/crackles, consider PA chest radiograph.",
    "Gastroenterology": "Abdominal palpation for tenderness/guarding, bowel sound auscultation, review NSAID/dietary history, LFTs/amylase if indicated.",
    "Dermatology": "Dermascopic inspection of lesions, skin barrier assessment, review of recent allergen/topical contact, patch test if indicated.",
    "General Medicine": "Complete vital signs check (BP, HR, Temp, SpO2), review systemic constitutional history, basic metabolic panel.",
    "Ophthalmology": "Visual acuity testing (Snellen chart), intraocular pressure measurement (tonometry), slit-lamp examination, fundoscopy.",
    "ENT": "Otoscopic ear canal inspection, anterior rhinoscopy for nasal mucosa/turbinates, pharyngeal exam for tonsillar erythema/exudate, tuning fork hearing check."
}

class HandoffAgent:
    """
    Handoff Agent (F3):
    Synthesizes intake data, token ID, department rationale, and allocated slot
    into a concise, structured Clinical Handoff Brief for the Doctor's portal queue.
    """
    @staticmethod
    def generate_brief(
        token_id: str,
        patient_name: str,
        patient_age: int,
        department: str,
        doctor_name: str,
        slot_timestamp: str,
        chief_complaint: str,
        duration: str,
        severity: int,
        associated_symptoms: list,
        triage_confidence: float,
        department_rationale: str,
        urgency_level: str
    ) -> str:
        suggested_workup = CLINICAL_WORKUP_SUGGESTIONS.get(department, "Standard physical examination and vitals measurement.")
        symptoms_list_str = ", ".join(associated_symptoms) if associated_symptoms else "None reported"

        brief = f"""### CLINICAL HANDOFF BRIEF | MAVIS Intake
**Token ID:** `{token_id}` | **Urgency:** `{urgency_level}` | **Department:** {department}
**Patient:** {patient_name} (Age: {patient_age}) | **Assigned To:** {doctor_name} | **Slot:** {slot_timestamp}

---
#### 1. Symptom Profile
- **Chief Complaint:** {chief_complaint}
- **Duration:** {duration}
- **Reported Severity:** {severity}/10
- **Associated Symptoms:** {symptoms_list_str}

#### 2. Triage Reasoning (Confidence: {int(triage_confidence * 100)}%)
{department_rationale}

#### 3. Recommended Initial Workup
{suggested_workup}
"""
        return brief.strip()

handoff_agent = HandoffAgent()
