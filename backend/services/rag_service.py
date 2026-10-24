import math
import re
from typing import Dict, List, Tuple

# Comprehensive clinical knowledge base mapping symptoms to departments
CLINICAL_KNOWLEDGE_BASE = [
    {
        "department": "Cardiology",
        "keywords": [
            "chest pain", "chest tightness", "palpitations", "racing heart", "high blood pressure",
            "hypertension", "irregular heartbeat", "shortness of breath on exertion", "heart flutter",
            "swelling in ankles", "edema in legs", "dizziness when standing", "angina", "murmur"
        ],
        "rationale": "Symptoms suggest cardiovascular etiology requiring ECG, echocardiogram, or cardiac evaluation.",
        "clarifying_question": "Do you feel this discomfort mainly in your chest, and does it worsen with physical exertion?"
    },
    {
        "department": "Neurology",
        "keywords": [
            "headache", "migraine", "severe headache", "numbness", "tingling in fingers", "tremors",
            "facial twitching", "loss of balance", "dizziness", "vertigo", "memory loss", "neuropathy",
            "seizure history", "frequent fainting", "pins and needles"
        ],
        "rationale": "Neurological presentation indicating central or peripheral nervous system evaluation.",
        "clarifying_question": "Are your headaches accompanied by visual changes, numbness, or tingling in your hands or feet?"
    },
    {
        "department": "Orthopedics",
        "keywords": [
            "joint pain", "knee pain", "back pain", "lower back ache", "shoulder pain", "bone fracture",
            "sprain", "swollen knee", "arthritis", "stiffness in morning", "sciatica", "hip pain",
            "ligament injury", "cannot bear weight", "elbow pain", "sports injury"
        ],
        "rationale": "Musculoskeletal complaint warranting orthopedic physical examination and radiological imaging.",
        "clarifying_question": "Did this pain start after a fall or injury, and does it limit joint movement?"
    },
    {
        "department": "Pulmonology",
        "keywords": [
            "cough", "chronic cough", "dry cough", "cough with phlegm", "wheezing", "asthma attack",
            "shortness of breath", "bronchitis", "chest congestion", "difficulty breathing at night",
            "smoker's cough", "lung congestion", "sputum"
        ],
        "rationale": "Respiratory symptoms requiring spirometry, chest auscultation, or pulmonary function tests.",
        "clarifying_question": "Have you been experiencing persistent wheezing or coughing up colored phlegm?"
    },
    {
        "department": "Gastroenterology",
        "keywords": [
            "stomach ache", "abdominal pain", "heartburn", "acid reflux", "gerd", "nausea",
            "vomiting", "diarrhea", "constipation", "bloating", "indigestion", "gastritis",
            "loss of appetite", "burning stomach", "stomach cramps"
        ],
        "rationale": "Gastrointestinal tract symptoms requiring dietary review, abdominal exam, or endoscopy.",
        "clarifying_question": "Is the stomach pain related to eating, or are you experiencing severe acid reflux and nausea?"
    },
    {
        "department": "Dermatology",
        "keywords": [
            "skin rash", "itching", "red patches", "eczema", "psoriasis", "hives", "urticaria",
            "acne breakout", "skin peeling", "dry scaly skin", "fungal infection", "mole changes",
            "blisters", "dermatitis"
        ],
        "rationale": "Integumentary condition requiring dermatoscopic examination and topical/systemic therapy.",
        "clarifying_question": "How long has the rash or skin itching been present, and has it spread to other areas?"
    },
    {
        "department": "General Medicine",
        "keywords": [
            "mild fever", "body ache", "fatigue", "general weakness", "malaise", "chills",
            "viral fever", "head cold", "runny nose", "sore throat", "routine health checkup",
            "feeling unwell", "loss of energy"
        ],
        "rationale": "Constitutional or generalized symptoms best initially evaluated by a General Physician.",
        "clarifying_question": "Do you have generalized fever, fatigue, or body aches without pain in a specific organ?"
    },
    {
        "department": "Ophthalmology",
        "keywords": [
            "blurry vision", "eye pain", "loss of vision", "red eye", "double vision", "eye strain",
            "cornea", "cataract", "glaucoma", "dry eyes", "itchy eyes", "watery eyes", "foreign body in eye",
            "swollen eyelid", "vision impairment", "floaters in eye"
        ],
        "rationale": "Ocular or ophthalmic presentation requiring visual acuity testing, slit-lamp examination, and eye care.",
        "clarifying_question": "Are you experiencing sudden vision changes, severe eye pain, or noticeable redness?"
    },
    {
        "department": "ENT",
        "keywords": [
            "ear pain", "ear ache", "ear discharge", "ringing in ears", "tinnitus", "sinus pain",
            "sinus congestion", "blocked nose", "sore throat", "tonsillitis", "hoarse voice", "hearing loss",
            "ear fullness", "throat irritation", "sinus pressure", "ear infection"
        ],
        "rationale": "Otorhinolaryngological presentation requiring otoscopic inspection, nasal endoscopy, or throat evaluation.",
        "clarifying_question": "Do you have pain or discharge in your ears, severe sinus congestion, or difficulty swallowing?"
    }
]

def tokenize_and_vectorize(text: str) -> Dict[str, float]:
    tokens = re.findall(r"\b[a-z]{3,}\b", text.lower())
    if not tokens:
        return {}
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    # Normalized vector
    norm = math.sqrt(sum(v * v for v in tf.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in tf.items()}

def cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    common = set(v1.keys()) & set(v2.keys())
    if not common:
        return 0.0
    return sum(v1[k] * v2[k] for k in common)

class RAGService:
    def __init__(self):
        self.doc_vectors = []
        for doc in CLINICAL_KNOWLEDGE_BASE:
            corpus = f"{doc['department']} " + " ".join(doc["keywords"]) + f" {doc['rationale']}"
            vec = tokenize_and_vectorize(corpus)
            self.doc_vectors.append({
                "department": doc["department"],
                "vector": vec,
                "keywords": doc["keywords"],
                "rationale": doc["rationale"],
                "clarifying_question": doc["clarifying_question"]
            })

    def match_department(self, chief_complaint: str, associated_symptoms: List[str] = None) -> Tuple[str, float, str, str]:
        """
        Calculates semantic similarity between patient symptoms and clinical department knowledge base.
        Returns: (department, confidence, rationale, clarifying_question)
        Threshold: 0.75
        """
        combined_text = chief_complaint + " " + " ".join(associated_symptoms or [])
        query_vec = tokenize_and_vectorize(combined_text)
        
        best_dept = "General Medicine"
        best_score = 0.0
        best_rationale = "General assessment recommended."
        best_clarifying = "Could you clarify the primary symptom causing you discomfort?"

        # 1. Direct keyword boost check
        lower_input = combined_text.lower()
        keyword_match_bonus: Dict[str, float] = {}

        for doc in self.doc_vectors:
            matches = sum(1 for kw in doc["keywords"] if kw in lower_input)
            keyword_match_bonus[doc["department"]] = min(matches * 0.28, 0.6)

        # 2. Vector Cosine Similarity
        for doc in self.doc_vectors:
            cos_sim = cosine_similarity(query_vec, doc["vector"])
            total_score = min(cos_sim * 0.65 + keyword_match_bonus.get(doc["department"], 0.0), 0.98)
            
            if total_score > best_score:
                best_score = total_score
                best_dept = doc["department"]
                best_rationale = doc["rationale"]
                best_clarifying = doc["clarifying_question"]

        # Confidence calibration: If direct keyword found, ensure high confidence
        if best_score < 0.4:
            # Low confidence ambiguity -> default to General Medicine with modest score
            return "General Medicine", round(best_score, 2), "Low specificity in symptoms; defaulted to General Medicine for initial triage.", best_clarifying
        
        return best_dept, round(best_score, 2), best_rationale, best_clarifying

rag_service = RAGService()
