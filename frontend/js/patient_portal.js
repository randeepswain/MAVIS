// Patient Portal - Public Token Tracker (Zero Login Required)
class PatientPortal {
  constructor() {
    this.currentToken = null;
    this.pollInterval = null;
  }

  async trackToken(tokenId) {
    const cleanToken = (tokenId || document.getElementById("patient-token-input").value || "").trim().toUpperCase();
    if (!cleanToken) {
      alert("Please enter a valid Token ID (e.g., CARD-20261020-001)");
      return;
    }

    this.currentToken = cleanToken;
    const resultContainer = document.getElementById("token-result-container");
    const errorContainer = document.getElementById("token-error-container");

    resultContainer.classList.add("hidden");
    errorContainer.classList.add("hidden");

    try {
      const res = await fetch(`/api/scheduling/token/${encodeURIComponent(cleanToken)}`);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Token not found.");
      }

      const data = await res.json();
      this.renderTokenDetails(data);
      resultContainer.classList.remove("hidden");

      // Set up auto-refresh every 10 seconds for live queue position updates
      if (this.pollInterval) clearInterval(this.pollInterval);
      this.pollInterval = setInterval(() => this.refreshSilently(), 10000);

    } catch (err) {
      errorContainer.innerHTML = `
        <div class="flex items-center space-x-2 text-rose-400">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          <span class="font-medium">${err.message}</span>
        </div>
      `;
      errorContainer.classList.remove("hidden");
    }
  }

  async refreshSilently() {
    if (!this.currentToken) return;
    try {
      const res = await fetch(`/api/scheduling/token/${encodeURIComponent(this.currentToken)}`);
      if (res.ok) {
        const data = await res.json();
        this.renderTokenDetails(data);
      }
    } catch (e) {
      console.log("Background poll error:", e);
    }
  }

  renderTokenDetails(data) {
    document.getElementById("pt-token-id").innerText = data.token_id;
    document.getElementById("pt-patient-name").innerText = data.patient_name;
    document.getElementById("pt-department").innerText = data.department;
    document.getElementById("pt-doctor").innerText = data.doctor_name;
    document.getElementById("pt-specialization").innerText = data.doctor_specialization;
    document.getElementById("pt-room").innerText = data.room_number;
    document.getElementById("pt-queue-pos").innerText = `#${data.queue_position}`;
    document.getElementById("pt-patients-ahead").innerText = `${data.patients_ahead} patient(s) ahead`;
    
    const slotDate = new Date(data.slot_time);
    document.getElementById("pt-slot-time").innerText = slotDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' (' + slotDate.toLocaleDateString() + ')';

    // Status Badge
    const statusBadge = document.getElementById("pt-status-badge");
    statusBadge.innerText = data.status;
    statusBadge.className = "px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider shadow-sm ";
    if (data.status === "SCHEDULED") statusBadge.className += "bg-blue-100 text-[#0084ff] border border-blue-200";
    else if (data.status === "IN_QUEUE") statusBadge.className += "bg-sky-100 text-sky-700 border border-sky-300 animate-pulse";
    else if (data.status === "IN_CONSULTATION") statusBadge.className += "bg-amber-100 text-amber-800 border border-amber-300";
    else if (data.status === "COMPLETED") statusBadge.className += "bg-emerald-100 text-emerald-800 border border-emerald-300";
    else statusBadge.className += "bg-slate-100 text-slate-700 border border-slate-200";

    // Follow-up status
    const fuEl = document.getElementById("pt-followup-status");
    fuEl.innerText = data.follow_up_status || "NOT_TRIGGERED";
    fuEl.className = "text-xs font-mono font-bold " + (
      data.follow_up_status === "CALLED_RECOVERING" ? "text-emerald-700" :
      data.follow_up_status === "CALLED_WORSENING" ? "text-amber-700" :
      data.follow_up_status === "ESCALATED_TO_DOCTOR" ? "text-rose-600 font-bold" : "text-slate-500"
    );
  }
}

window.patientPortal = new PatientPortal();
