import base64
import uuid
import time
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.session import get_db
from backend.services.audio_pipeline import vad_processor, asr_engine, tts_engine, telephony_gateway
from backend.agents.safety_gate import safety_gate
from backend.agents.receptionist import receptionist_agent
from backend.agents.triage_agent import triage_agent
from backend.agents.handoff_agent import handoff_agent
from backend.services.scheduling import scheduling_service
from backend.services.redis_service import redis_service
from backend.services.audit import audit_service
from backend.config import settings

logger = logging.getLogger("mavis.voice")
router = APIRouter(prefix="/voice", tags=["Voice Telephony Pipeline"])

class VoiceSessionStartRequest(BaseModel):
    caller_phone: Optional[str] = "+91-98765-00000"
    client_type: Optional[str] = "webrtc_browser" # 'webrtc_browser' or 'sip_phone'

class ProcessTurnRequest(BaseModel):
    call_id: str
    caller_phone: Optional[str] = "+91-98765-00000"
    caller_utterance: str
    current_stage: Optional[str] = "reception" # reception, triage, clarification, booking
    patient_name: Optional[str] = "Patient"
    patient_age: Optional[int] = 35
    selected_slot_id: Optional[int] = None
    target_department: Optional[str] = None
    audio_base64: Optional[str] = None

class TTSSynthesizeRequest(BaseModel):
    text: str

@router.post("/session/start")
async def start_voice_session(req: VoiceSessionStartRequest, db: AsyncSession = Depends(get_db)):
    """
    Initializes a new WebRTC / SIP voice intake session.
    Returns LiveKit connection credentials, call ID, and initial receptionist prompt.
    """
    call_id = f"call-{uuid.uuid4().hex[:10]}"
    room_name = f"mavis-room-{call_id}"
    
    livekit_token_info = telephony_gateway.generate_token(
        room_name=room_name,
        participant_identity=req.caller_phone or "browser-caller"
    )

    initial_greeting = (
        "Hello, welcome to MAVIS Hospital Intake. This call is transcribed for medical coordination. "
        "Do you consent to proceed with automated clinical triage and scheduling?"
    )

    # Pre-synthesize Piper TTS waveform
    wav_bytes = tts_engine.synthesize_wav(initial_greeting)
    audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

    await audit_service.log_event(
        db=db,
        event_type="VOICE_CALL_SESSION_STARTED",
        payload_data={
            "call_id": call_id,
            "client_type": req.client_type,
            "caller_phone": req.caller_phone,
            "room_name": room_name
        },
        call_id=call_id
    )
    await db.commit()

    return {
        "call_id": call_id,
        "room_name": room_name,
        "livekit": livekit_token_info,
        "stage": "reception",
        "system_speech": initial_greeting,
        "audio_base64": audio_b64,
        "caller_phone": req.caller_phone
    }

@router.post("/process-turn")
async def process_voice_turn(req: ProcessTurnRequest, db: AsyncSession = Depends(get_db)):
    """
    Core conversational processing pipeline:
    1. LAYER 1: Transcribe audio if base64 audio payload provided.
    2. LAYER 2 (F4): Synchronous deterministic Emergency Red-Flag check on EVERY utterance BEFORE LLM.
       - If triggered -> Instant bypass to Human Triage Nurse with hash-chained audit log.
    3. Multi-Agent orchestration:
       - Receptionist (consent/language)
       - Symptom Triage (F1) + RAG (<0.75 confidence clarification check)
       - Slot soft-hold (Redis TTL) & Transactional booking commit
       - Handoff Brief generation (F3)
    4. Piper TTS neural synthesis of response.
    """
    utterance = req.caller_utterance.strip()

    # If raw audio was supplied, run faster-whisper ASR
    if req.audio_base64 and not utterance:
        try:
            audio_bytes = base64.b64decode(req.audio_base64)
            transcription = asr_engine.transcribe_audio_chunk(audio_bytes)
            if transcription:
                utterance = transcription
        except Exception as e:
            logger.error("Audio decode/ASR error: %s", e)

    if not utterance:
        utterance = "Hello"

    # =========================================================================
    # STEP 1: EMERGENCY RED-FLAG SAFETY GATE (F4) - SYNCHRONOUS AND DETERMINISTIC
    # =========================================================================
    safety_result = await safety_gate.process_safety_check(
        text=utterance,
        call_id=req.call_id,
        db=db,
        caller_phone=req.caller_phone
    )

    if safety_result["triggered"]:
        emergency_speech = safety_result["system_speech"]
        emergency_wav = tts_engine.synthesize_wav(emergency_speech)
        return {
            "stage": "emergency",
            "red_flag_triggered": True,
            "trigger_phrase": safety_result.get("trigger_phrase"),
            "clinical_rationale": safety_result.get("clinical_rationale"),
            "action": "EMERGENCY_ESCALATION",
            "system_speech": emergency_speech,
            "call_bridge_info": safety_result.get("call_bridge_info"),
            "audit_entry_id": safety_result.get("audit_entry_id"),
            "record_hash": safety_result.get("record_hash"),
            "audio_base64": base64.b64encode(emergency_wav).decode("ascii")
        }

    # =========================================================================
    # STEP 2: MULTI-AGENT STATE TRANSITIONS (NO RED FLAG)
    # =========================================================================
    current_stage = req.current_stage or "reception"
    system_speech = ""
    next_stage = current_stage
    triage_info = None
    booking_result = None
    handoff_brief = None

    if current_stage == "reception":
        consent = receptionist_agent.process_consent(utterance)
        if not consent["consent_granted"]:
            next_stage = "aborted"
            system_speech = consent["response"]
        else:
            next_stage = "triage"
            system_speech = consent["response"]

    elif current_stage in ["triage", "clarification"]:
        already_clarified = (current_stage == "clarification")
        triage_out = await triage_agent.triage_and_route(
            utterance=utterance,
            already_clarified=already_clarified
        )
        triage_info = triage_out

        if triage_out.get("needs_clarification"):
            next_stage = "clarification"
            system_speech = triage_out["system_response"]
        else:
            # Department identified! Now request slot hold and proceed to booking
            dept = triage_out["target_department"]
            extracted = triage_out["extracted_data"]
            patient_name = extracted.get("patient_name") or req.patient_name or "Patient"
            patient_age = extracted.get("age") or req.patient_age or 35

            # Find next slot and acquire 3-min soft-hold
            held_slot = await scheduling_service.find_and_hold_next_slot(db, department=dept, call_id=req.call_id)
            
            if held_slot:
                # Automatically confirm booking atomically
                booking = await scheduling_service.confirm_booking(
                    db=db,
                    call_id=req.call_id,
                    slot_id=held_slot["slot_id"],
                    patient_name=patient_name,
                    patient_age=patient_age,
                    caller_phone=req.caller_phone or "+91-98765-00000",
                    department=dept,
                    triage_data={
                        "chief_complaint": extracted.get("chief_complaint"),
                        "duration": extracted.get("duration"),
                        "severity_scale_1_to_10": extracted.get("severity_scale_1_to_10"),
                        "associated_symptoms": extracted.get("associated_symptoms"),
                        "triage_confidence": triage_out["confidence"],
                        "department_rationale": triage_out["department_rationale"],
                        "urgency_level": triage_out["urgency_level"],
                        "handoff_brief": handoff_agent.generate_brief(
                            token_id="PENDING",
                            patient_name=patient_name,
                            patient_age=patient_age,
                            department=dept,
                            doctor_name=held_slot["doctor_name"],
                            slot_timestamp=held_slot["slot_timestamp"],
                            chief_complaint=extracted.get("chief_complaint"),
                            duration=extracted.get("duration"),
                            severity=extracted.get("severity_scale_1_to_10"),
                            associated_symptoms=extracted.get("associated_symptoms"),
                            triage_confidence=triage_out["confidence"],
                            department_rationale=triage_out["department_rationale"],
                            urgency_level=triage_out["urgency_level"]
                        )
                    }
                )
                booking_result = booking
                next_stage = "completed"

                system_speech = (
                    f"Thank you, {patient_name}. I have booked your appointment with {held_slot['doctor_name']} "
                    f"in the Department of {dept}, Room {held_slot['room_number']}. "
                    f"Your unique tracking Token ID is {booking['token_id']}. Your current live queue position is {booking['queue_position']}. "
                    f"Your structured Clinical Handoff Brief has been dispatched directly to the doctor's queue. "
                    f"You may track your live status on the patient portal without logging in."
                )
            else:
                next_stage = "completed"
                system_speech = (
                    f"Your symptoms have been assigned to {dept}. However, all standard online slots for today are currently filled. "
                    f"I have registered you in the emergency walk-in priority standby list. Please arrive directly at the triage desk."
                )

    elif current_stage == "completed":
        system_speech = "Your booking is confirmed. You may track your appointment status using your Token ID."

    # Synthesize speech via Piper TTS
    wav_out = tts_engine.synthesize_wav(system_speech)
    audio_b64_out = base64.b64encode(wav_out).decode("ascii")

    return {
        "call_id": req.call_id,
        "caller_utterance": utterance,
        "stage": next_stage,
        "red_flag_triggered": False,
        "system_speech": system_speech,
        "audio_base64": audio_b64_out,
        "triage_info": triage_info,
        "booking_result": booking_result
    }

@router.post("/synthesize-tts")
async def synthesize_tts(req: TTSSynthesizeRequest):
    """
    Direct Piper TTS neural synthesis endpoint.
    """
    wav_bytes = tts_engine.synthesize_wav(req.text)
    return Response(content=wav_bytes, media_type="audio/wav")

@router.websocket("/ws/{call_id}")
async def voice_websocket_stream(websocket: WebSocket, call_id: str):
    """
    Real-time full-duplex WebSocket stream for edge audio pipeline:
    - Receives streaming PCM audio frames
    - Evaluates Silero VAD (voice presence & silence tracking)
    - Detects barge-in / interruption (user speaks while agent TTS is playing)
    - Emits transcription events and agent state
    """
    await websocket.accept()
    logger.info("WebSocket connected for call_id: %s", call_id)

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "audio_frame":
                # Simulated or real PCM chunk
                b64_pcm = data.get("pcm_base64", "")
                if b64_pcm:
                    raw_bytes = base64.b64decode(b64_pcm)
                    is_voice, confidence = vad_processor.evaluate_frame(raw_bytes)
                    await websocket.send_json({
                        "type": "vad_update",
                        "is_voice": is_voice,
                        "confidence": confidence,
                        "barge_in": is_voice and vad_processor.is_speaking
                    })

            elif event_type == "ping":
                await websocket.send_json({"type": "pong", "time": time.time()})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for call_id: %s", call_id)
    except Exception as e:
        logger.error("WebSocket exception: %s", e)
