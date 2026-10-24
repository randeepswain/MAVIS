// Doctor Portal Logic - Queue, Handoff Briefs & Follow-up Reviewer
class DoctorPortal {
  constructor() {
    this.token = localStorage.getItem("mavis_token") || null;
    this.currentDoctor = null;
  }

  setToken(token) {
    this.token = token;
  }

  async loadDashboard() {
    if (!this.token) return;

    try {
      const res = await fetch("/api/doctor/queue", {
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      if (!res.ok) throw new Error("Failed to load doctor queue.");

      const data = await res.json();
      this.currentDoctor = data;

      document.getElementById("doc-name-display").innerText = data.doctor_name;
      document.getElementById("doc-dept-display").innerText = `${data.department} • Room ${data.room_number}`;
      
      this.renderQueueTable(data.queue);
      this.loadFollowUps();
    } catch (err) {
      console.error("Doctor dashboard error:", err);
    }
  }

  renderQueueTable(queue) {
    const tbody = document.getElementById("doctor-queue-tbody");
    tbody.innerHTML = "";

    if (!queue || queue.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-slate-400">No active appointments scheduled.</td></tr>`;
      return;
    }

    queue.forEach(item => {
      const tr = document.createElement("tr");
      tr.className = "border-b border-slate-100 hover:bg-blue-50/40 transition text-sm";
      
      const timeStr = new Date(item.slot_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      
      const urgencyBadge = item.urgency_level === "URGENT" || item.severity_scale >= 7
        ? `<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">URGENT (${item.severity_scale}/10)</span>`
        : `<span class="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">ROUTINE (${item.severity_scale}/10)</span>`;

      tr.innerHTML = `
        <td class="py-3 px-4 font-mono font-bold text-[#0084ff]">${item.token_id}</td>
        <td class="py-3 px-4 font-semibold text-slate-700">${timeStr}</td>
        <td class="py-3 px-4 font-bold text-[#1e1b4b]">${item.patient_name} <span class="text-xs text-slate-400 font-normal">(${item.patient_age}y)</span></td>
        <td class="py-3 px-4 text-slate-600 truncate max-w-xs">${item.chief_complaint}</td>
        <td class="py-3 px-4">${urgencyBadge}</td>
        <td class="py-3 px-4">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-bold ${
            item.status === 'IN_CONSULTATION' ? 'bg-amber-100 text-amber-800 border border-amber-200' :
            item.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' :
            'bg-blue-100 text-[#0084ff] border border-blue-200'
          }">${item.status}</span>
        </td>
        <td class="py-3 px-4 text-right space-x-1.5">
          <button onclick="window.doctorPortal.openHandoffBrief(${item.appointment_id})" class="px-3 py-1 rounded-full bg-[#0084ff] hover:bg-[#0070d6] text-white text-xs font-bold transition shadow-sm">
            View AI Brief
          </button>
          ${item.status !== 'COMPLETED' ? `
            <button onclick="window.doctorPortal.updateStatus(${item.appointment_id}, 'IN_CONSULTATION')" class="px-3 py-1 rounded-full bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold transition shadow-sm" title="Call Patient">
              Call
            </button>
            <button onclick="window.doctorPortal.completeAppointment(${item.appointment_id})" class="px-3 py-1 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition shadow-sm" title="Mark Completed">
              Done
            </button>
          ` : `
            <button onclick="window.doctorPortal.triggerFollowUp(${item.appointment_id})" class="px-3 py-1 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition shadow-sm" title="Trigger F5 Follow-Up Call">
              Follow-Up
            </button>
          `}
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  async openHandoffBrief(appointmentId) {
    try {
      const res = await fetch(`/api/doctor/brief/${appointmentId}`, {
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      if (!res.ok) throw new Error("Could not fetch handoff brief.");
      const data = await res.json();

      document.getElementById("modal-brief-title").innerText = `Clinical Handoff: ${data.patient_name} (Token ${data.token_id})`;
      document.getElementById("modal-brief-content").innerHTML = `
        <div class="space-y-4 text-slate-700 text-sm">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 bg-blue-50/60 p-3.5 rounded-2xl border border-blue-100">
            <div><span class="text-xs text-slate-500 font-semibold block">Patient</span><strong class="text-[#1e1b4b]">${data.patient_name} (${data.patient_age}y)</strong></div>
            <div><span class="text-xs text-slate-500 font-semibold block">Token / Slot</span><strong class="text-[#0084ff] font-mono">${data.token_id}</strong></div>
            <div><span class="text-xs text-slate-500 font-semibold block">Urgency</span><strong class="${data.urgency_level === 'URGENT' ? 'text-rose-600' : 'text-emerald-600'}">${data.urgency_level}</strong></div>
            <div><span class="text-xs text-slate-500 font-semibold block">AI Triage Match</span><strong class="text-indigo-700">${data.department} (${Math.round(data.triage_confidence * 100)}%)</strong></div>
          </div>

          <div class="bg-slate-50 p-4 rounded-2xl border border-slate-200">
            <h4 class="text-xs uppercase font-bold text-slate-600 tracking-wider mb-2">1. Patient Reported Symptoms</h4>
            <div class="space-y-1 text-slate-800">
              <div><strong>Chief Complaint:</strong> ${data.chief_complaint}</div>
              <div><strong>Duration:</strong> ${data.duration}</div>
              <div><strong>Reported Severity:</strong> ${data.severity_scale} / 10</div>
            </div>
          </div>

          <div class="bg-blue-50/50 p-4 rounded-2xl border border-blue-100">
            <h4 class="text-xs uppercase font-bold text-[#0084ff] tracking-wider mb-1">2. AI Triage Rationale & Evidence</h4>
            <p class="text-xs text-slate-700 font-medium">${data.department_rationale}</p>
          </div>

          <div class="bg-emerald-50/50 p-4 rounded-2xl border border-emerald-200">
            <h4 class="text-xs uppercase font-bold text-emerald-800 tracking-wider mb-1">3. Recommended Clinical Workup</h4>
            <pre class="text-xs text-emerald-900 whitespace-pre-wrap font-sans font-medium">${data.handoff_brief}</pre>
          </div>
        </div>
      `;
      document.getElementById("brief-modal").classList.remove("hidden");
    } catch (err) {
      alert("Error loading brief: " + err.message);
    }
  }

  async updateStatus(appointmentId, status) {
    try {
      await fetch(`/api/doctor/appointment/${appointmentId}/status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.token}`
        },
        body: JSON.stringify({ status })
      });
      this.loadDashboard();
    } catch (err) {
      alert("Status update failed: " + err.message);
    }
  }

  async completeAppointment(appointmentId) {
    const notes = prompt("Enter consultation summary notes (optional):", "Routine consultation completed, patient stable.");
    if (notes === null) return;
    
    try {
      await fetch(`/api/doctor/appointment/${appointmentId}/status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.token}`
        },
        body: JSON.stringify({ status: "COMPLETED", consultation_notes: notes })
      });
      this.loadDashboard();
    } catch (err) {
      alert("Completion failed: " + err.message);
    }
  }

  async triggerFollowUp(appointmentId) {
    const simulationAnswer = prompt(
      "Simulate patient follow-up response (e.g. 'Feeling much better' or 'My symptoms got worse, severe knee pain'):",
      "Condition is improving, swelling has subsided with ice."
    );
    if (!simulationAnswer) return;

    try {
      const res = await fetch(`/api/doctor/appointment/${appointmentId}/trigger-followup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.token}`
        },
        body: JSON.stringify({ simulated_patient_response: simulationAnswer })
      });
      const data = await res.json();
      alert(`Follow-up Agent Result: Condition recorded as '${data.recovery_condition}'. Speech: "${data.system_speech}"`);
      this.loadDashboard();
    } catch (err) {
      alert("Follow-up trigger failed: " + err.message);
    }
  }

  async loadFollowUps() {
    try {
      const res = await fetch("/api/doctor/followups", {
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      if (!res.ok) return;
      const data = await res.json();

      const tbody = document.getElementById("doctor-followups-tbody");
      if (!tbody) return;
      tbody.innerHTML = "";

      if (!data.follow_ups || data.follow_ups.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-slate-400">No post-visit follow-up records yet.</td></tr>`;
        return;
      }

      data.follow_ups.forEach(fu => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-100 hover:bg-blue-50/40 text-xs";
        
        const condClass = fu.recovery_condition === 'RECOVERED' || fu.recovery_condition === 'IMPROVING'
          ? 'text-emerald-700 font-bold'
          : fu.recovery_condition === 'WORSENING' || fu.escalated_to_doctor
          ? 'text-rose-600 font-bold animate-pulse'
          : 'text-slate-600';

        tr.innerHTML = `
          <td class="py-3 px-4 font-mono font-bold text-[#0084ff]">${fu.token_id}</td>
          <td class="py-3 px-4 font-bold text-[#1e1b4b]">${fu.patient_name}</td>
          <td class="py-3 px-4 text-slate-600 italic truncate max-w-xs">"${fu.patient_feedback || 'N/A'}"</td>
          <td class="py-3 px-4 ${condClass}">${fu.recovery_condition}</td>
          <td class="py-3 px-4">${fu.escalated_to_doctor ? '<span class="text-rose-600 font-bold">⚠️ ESCALATED</span>' : '<span class="text-slate-500 font-medium">Normal</span>'}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.log("Followups error:", e);
    }
  }
}

window.doctorPortal = new DoctorPortal();
