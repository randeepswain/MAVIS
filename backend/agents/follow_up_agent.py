import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database.models import Appointment, FollowUpRecord
from backend.agents.safety_gate import safety_gate
from backend.services.audit import audit_service

class FollowUpAgent:
    """
    Post-Visit Follow-Up Agent (F5):
    - Triggered by automated scheduler post-visit.
    - Queries recovery progress and patient feedback.
    - Routes worsening conditions back through F4 Safety Gate.
    - Alerts the attending physician and writes follow-up status.
    """
    @staticmethod
    async def evaluate_patient_response(
        db: AsyncSession,
        appointment_id: int,
        patient_utterance: str,
        call_id: Optional[str] = None
    ) -> Dict[str, Any]:
        call_id = call_id or f"followup-{appointment_id}-{int(datetime.datetime.now().timestamp())}"
        
        # 1. First run patient response through F4 Safety Gate!
        safety_result = await safety_gate.process_safety_check(
            text=patient_utterance,
            call_id=call_id,
            db=db
        )

        # Fetch appointment
        apt_stmt = select(Appointment).where(Appointment.id == appointment_id)
        apt_res = await db.execute(apt_stmt)
        appointment = apt_res.scalars().first()

        if not appointment:
            return {"success": False, "error": "Appointment not found."}

        # If red-flag triggered during follow-up
        if safety_result["triggered"]:
            appointment.follow_up_status = "ESCALATED_TO_DOCTOR"
            
            followup = FollowUpRecord(
                appointment_id=appointment.id,
                call_id=call_id,
                scheduled_at=datetime.datetime.now(datetime.timezone.utc),
                executed_at=datetime.datetime.now(datetime.timezone.utc),
                patient_feedback=patient_utterance,
                recovery_condition="RED_FLAG",
                escalated_to_doctor=True,
                doctor_alert_notes=f"CRITICAL RED FLAG DETECTED DURING FOLLOW-UP: {safety_result.get('trigger_phrase')}."
            )
            db.add(followup)

            await audit_service.log_event(
                db=db,
                event_type="FOLLOWUP_EMERGENCY_ESCALATION",
                call_id=call_id,
                payload_data={
                    "appointment_id": appointment.id,
                    "token_id": appointment.token_id,
                    "trigger_phrase": safety_result.get("trigger_phrase"),
                    "feedback": patient_utterance
                }
            )
            await db.commit()

            return {
                "status": "EMERGENCY_ESCALATED",
                "recovery_condition": "RED_FLAG",
                "system_speech": safety_result["system_speech"],
                "escalated": True,
                "token_id": appointment.token_id
            }

        # Evaluate condition
        lower = patient_utterance.lower()
        condition = "IMPROVING"
        escalate = False
        doctor_notes = None

        if any(w in lower for w in ["worse", "worsening", "more pain", "higher fever", "cannot walk", "not helping", "severe pain"]):
            condition = "WORSENING"
            escalate = True
            appointment.follow_up_status = "CALLED_WORSENING"
            doctor_notes = f"Patient reported worsening symptoms post-consultation: '{patient_utterance}'"
            response_speech = (
                "We have recorded that your symptoms have worsened. I have flagged this directly to your attending physician's portal "
                "for priority review. If you experience severe chest pain or difficulty breathing, please seek immediate emergency care."
            )
        elif any(w in lower for w in ["recovered", "completely fine", "all good", "cured", "no pain", "much better"]):
            condition = "RECOVERED"
            appointment.follow_up_status = "COMPLETED"
            response_speech = "We are glad to hear you have recovered! Thank you for choosing MAVIS healthcare."
        elif any(w in lower for w in ["improving", "better", "recovering", "slight improvement"]):
            condition = "IMPROVING"
            appointment.follow_up_status = "CALLED_RECOVERING"
            response_speech = "Thank you for the update. It is good to hear your condition is improving. Please continue your prescribed course."
        else:
            condition = "SAME"
            appointment.follow_up_status = "CALLED_RECOVERING"
            response_speech = "Thank you for the update. If your symptoms do not improve over the next 24 to 48 hours, please schedule a follow-up."

        followup = FollowUpRecord(
            appointment_id=appointment.id,
            call_id=call_id,
            scheduled_at=datetime.datetime.now(datetime.timezone.utc),
            executed_at=datetime.datetime.now(datetime.timezone.utc),
            patient_feedback=patient_utterance,
            recovery_condition=condition,
            escalated_to_doctor=escalate,
            doctor_alert_notes=doctor_notes
        )
        db.add(followup)

        await audit_service.log_event(
            db=db,
            event_type="FOLLOWUP_STATUS_RECORDED",
            call_id=call_id,
            payload_data={
                "appointment_id": appointment.id,
                "token_id": appointment.token_id,
                "condition": condition,
                "escalated": escalate
            }
        )
        await db.commit()

        return {
            "status": "RECORDED",
            "recovery_condition": condition,
            "escalated": escalate,
            "system_speech": response_speech,
            "token_id": appointment.token_id
        }

follow_up_agent = FollowUpAgent()
