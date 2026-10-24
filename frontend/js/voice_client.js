// MAVIS Voice Client & LiveKit / WebRTC Telephony Simulator
class MavisVoiceClient {
  constructor() {
    this.callId = null;
    this.stage = "reception";
    this.callerPhone = "+91-98765-43210";
    this.patientName = "Rohan Sharma";
    this.patientAge = 42;
    this.isPlayingAudio = false;
    this.currentAudio = null;
    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
  }

  getTranscriptEl() {
    return document.getElementById("voice-transcript") || document.getElementById("transcript-container");
  }

  setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  toggleEl(id, show) {
    const el = document.getElementById(id);
    if (el) {
      if (show) el.classList.remove("hidden");
      else el.classList.add("hidden");
    }
  }

  async startCall() {
    this.setHtml("voice-status", `<span class="inline-block w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping mr-2"></span>Connecting to LiveKit WebRTC Gateway...`);

    try {
      const res = await fetch("/api/voice/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          caller_phone: this.callerPhone,
          client_type: "webrtc_browser"
        })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Voice Gateway connection failed");
      }
      const data = await res.json();
      this.callId = data.call_id;
      this.stage = data.stage;

      this.setHtml("voice-status", `<span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 mr-2"></span>Connected: ${this.callId} | LiveKit WebRTC Active`);
      
      this.appendMessage("agent", data.system_speech);
      if (data.audio_base64) {
        this.playAudioB64(data.audio_base64);
      }

      this.toggleEl("btn-start-call", false);
      this.toggleEl("btn-end-call", true);
      this.toggleEl("voice-controls", true);
      this.toggleEl("voice-waveform", true);
    } catch (err) {
      this.setHtml("voice-status", `<span class="text-rose-500 font-bold">Connection Failed: ${err.message}</span>`);
      console.error("Voice startCall error:", err);
    }
  }

  async endCall() {
    this.stopAudio();
    this.callId = null;
    this.stage = "reception";
    this.setHtml("voice-status", `<span class="text-slate-400">Call Disconnected</span>`);
    this.toggleEl("btn-start-call", true);
    this.toggleEl("btn-end-call", false);
    this.toggleEl("voice-controls", false);
    this.toggleEl("voice-waveform", false);
  }

  async sendTurn(utterance) {
    if (!this.callId) {
      await this.startCall();
    }

    this.stopAudio(); // Barge-in interruption on user speech
    this.appendMessage("user", utterance);

    this.setHtml("voice-status", `<span class="inline-block w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse mr-2"></span>F4 Safety Gate & Multi-Agent Processing...`);

    try {
      const res = await fetch("/api/voice/process-turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          call_id: this.callId,
          caller_phone: this.callerPhone,
          caller_utterance: utterance,
          current_stage: this.stage,
          patient_name: this.patientName,
          patient_age: parseInt(this.patientAge)
        })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Turn processing failed");
      }
      const data = await res.json();

      if (data.red_flag_triggered) {
        // Red flag emergency trigger!
        this.stage = "emergency";
        this.setHtml("voice-status", `<span class="inline-block w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping mr-2"></span>EMERGENCY BYPASS ACTIVE - Live Call Bridge Initiated`);
        this.appendEmergencyAlert(data);
      } else {
        this.stage = data.stage;
        this.setHtml("voice-status", `<span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 mr-2"></span>Stage: ${data.stage.toUpperCase()}`);
        this.appendMessage("agent", data.system_speech);

        if (data.booking_result && data.booking_result.token_id) {
          this.appendBookingCard(data.booking_result);
        }
      }

      if (data.audio_base64) {
        this.playAudioB64(data.audio_base64);
      }
    } catch (err) {
      this.setHtml("voice-status", `<span class="text-rose-500 font-bold">Processing Error: ${err.message}</span>`);
      console.error("Voice sendTurn error:", err);
    }
  }

  // Interruption / Barge-in trigger
  triggerBargeIn() {
    if (this.isPlayingAudio) {
      this.stopAudio();
      this.setHtml("voice-status", `<span class="inline-block w-2.5 h-2.5 rounded-full bg-amber-400 mr-2"></span>Barge-in Triggered! Silero VAD detected user voice interruption.`);
      const transcriptEl = this.getTranscriptEl();
      if (transcriptEl) {
        const banner = document.createElement("div");
        banner.className = "p-2 my-2 text-xs rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-center";
        banner.innerText = "⚡ BARGE-IN EVENT: Agent TTS paused. Silero VAD listening to caller.";
        transcriptEl.appendChild(banner);
        transcriptEl.scrollTop = transcriptEl.scrollHeight;
      }
    }
  }

  playAudioB64(b64Data) {
    this.stopAudio();
    this.currentAudio = new Audio("data:audio/wav;base64," + b64Data);
    this.isPlayingAudio = true;
    this.toggleEl("agent-speaking-indicator", true);

    this.currentAudio.onended = () => {
      this.isPlayingAudio = false;
      this.toggleEl("agent-speaking-indicator", false);
    };
    this.currentAudio.play().catch(e => console.log("Audio autoplay prevented:", e));
  }

  stopAudio() {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    this.isPlayingAudio = false;
    this.toggleEl("agent-speaking-indicator", false);
  }

  appendMessage(role, text) {
    const transcriptEl = this.getTranscriptEl();
    if (!transcriptEl) return;

    // Clear initial greeting placeholder if present
    const placeholder = document.getElementById("voice-placeholder-msg");
    if (placeholder) placeholder.remove();

    const msgDiv = document.createElement("div");
    msgDiv.className = `p-3.5 rounded-2xl text-sm max-w-[85%] my-2 shadow-sm ${
      role === "user" 
        ? "ml-auto bg-[#0084ff] text-white rounded-tr-none font-medium" 
        : "mr-auto bg-white border border-blue-200 text-slate-800 rounded-tl-none"
    }`;
    msgDiv.innerHTML = `<div class="text-[10px] uppercase font-bold tracking-wider mb-1 ${role === "user" ? "text-blue-100 text-right" : "text-[#0084ff]"}">
      ${role === "user" ? "Caller (Spoken Audio)" : "MAVIS Voice Agent (Piper TTS)"}
    </div><div>${text}</div>`;
    transcriptEl.appendChild(msgDiv);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  appendEmergencyAlert(data) {
    const transcriptEl = this.getTranscriptEl();
    if (!transcriptEl) return;

    const placeholder = document.getElementById("voice-placeholder-msg");
    if (placeholder) placeholder.remove();

    const alertDiv = document.createElement("div");
    alertDiv.className = "p-4 rounded-2xl border border-rose-300 bg-rose-50 text-rose-900 my-3 shadow-md";
    alertDiv.innerHTML = `
      <div class="flex items-center space-x-2 text-rose-700 font-extrabold mb-2">
        <svg class="w-5 h-5 animate-pulse text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
        <span>F4 ZERO-TOLERANCE RED-FLAG SAFETY GATE TRIGGERED</span>
      </div>
      <p class="text-xs text-rose-800 mb-2"><strong>Trigger Phrase Detected:</strong> "${data.trigger_phrase || 'Critical Symptom'}"</p>
      <p class="text-xs text-rose-800 mb-2"><strong>Clinical Rationale:</strong> ${data.clinical_rationale || 'Immediate emergency medical intervention indicated.'}</p>
      <div class="bg-white/90 p-3 rounded-xl border border-rose-200 text-xs mb-3 space-y-1">
        <div class="font-bold text-rose-900">Live Call Bridge Active:</div>
        <div>Transferred To: <span class="text-rose-700 font-mono font-bold">${data.call_bridge_info?.phone_number || '112 / 108'}</span> (Triage Desk)</div>
        <div>Emergency Fallbacks: <span class="text-rose-700 font-mono font-bold">112 / 108</span></div>
      </div>
      <div class="text-[11px] text-rose-600 font-mono">
        SHA-256 Audit Hash: ${data.record_hash ? data.record_hash.substring(0, 24) + '...' : 'Recorded in Tamper-Proof Chain'}
      </div>
    `;
    transcriptEl.appendChild(alertDiv);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  appendBookingCard(booking) {
    const transcriptEl = this.getTranscriptEl();
    if (!transcriptEl) return;

    const placeholder = document.getElementById("voice-placeholder-msg");
    if (placeholder) placeholder.remove();

    const card = document.createElement("div");
    card.className = "p-4 rounded-2xl border border-emerald-300 bg-emerald-50 text-emerald-900 my-3 shadow-md";
    card.innerHTML = `
      <div class="flex items-center justify-between mb-2">
        <span class="text-emerald-700 font-bold text-sm">✓ APPOINTMENT CONFIRMED (FCFS)</span>
        <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-white text-emerald-700 border border-emerald-300 shadow-sm">Queue #${booking.queue_position}</span>
      </div>
      <div class="text-xs space-y-1 mb-3">
        <div><strong>Token ID:</strong> <span class="font-mono text-[#0084ff] text-sm font-bold">${booking.token_id}</span></div>
        <div><strong>Department:</strong> ${booking.department}</div>
        <div><strong>Doctor:</strong> ${booking.doctor_name} (${booking.room_number})</div>
        <div><strong>Slot:</strong> ${new Date(booking.slot_timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
      </div>
      <button onclick="window.loadTokenInTracker('${booking.token_id}')" class="w-full py-2 px-3 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition shadow-sm">
        Track Live Status in Patient Portal →
      </button>
    `;
    transcriptEl.appendChild(card);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;

    // Update the sidebar booking card as well
    const cardToken = document.getElementById("card-token-id");
    const cardQueue = document.getElementById("card-queue-pos");
    const cardDoctor = document.getElementById("card-doctor");
    const cardSlot = document.getElementById("card-slot");
    if (cardToken) cardToken.innerText = booking.token_id;
    if (cardQueue) cardQueue.innerText = `#${booking.queue_position}`;
    if (cardDoctor) cardDoctor.innerText = `${booking.doctor_name} (${booking.room_number})`;
    if (cardSlot) cardSlot.innerText = new Date(booking.slot_timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    this.toggleEl("booking-confirmed-card", true);
  }
}

window.voiceClient = new MavisVoiceClient();
