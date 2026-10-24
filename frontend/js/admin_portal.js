// Admin Portal Logic - Telemetry, Doctor Rosters, and Hash-Chained Audit Logs
class AdminPortal {
  constructor() {
    this.token = localStorage.getItem("mavis_token") || null;
  }

  setToken(token) {
    this.token = token;
  }

  async loadDashboard() {
    if (!this.token) return;
    await Promise.all([
      this.loadTelemetry(),
      this.loadDoctors(),
      this.loadAuditLogs()
    ]);
  }

  async loadTelemetry() {
    try {
      const res = await fetch("/api/admin/telemetry", {
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      if (!res.ok) return;
      const data = await res.json();

      const setTxt = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
      };

      setTxt("tel-call-completion", `${data.call_completion_rate}%`);
      setTxt("tel-slot-utilization", `${data.slot_utilization_pct}%`);
      setTxt("tel-under-triage", `${data.under_triage_rate}%`);
      setTxt("tel-avg-wait", `${data.average_wait_minutes} min`);
      setTxt("tel-total-apt", data.total_appointments);
      setTxt("tel-red-flags", data.emergency_red_flags_prevented);

      setTxt("adm-stat-appointments", data.total_appointments ?? "--");
      setTxt("adm-stat-emergencies", data.emergency_red_flags_prevented ?? "--");
      setTxt("adm-stat-doctors", data.total_doctors ?? data.active_doctors ?? "--");
      setTxt("adm-stat-audit", data.total_audit_events ?? data.audit_events_count ?? "--");
    } catch (err) {
      console.error("Telemetry load error:", err);
    }
  }

  async loadDoctors() {
    try {
      const res = await fetch("/api/admin/doctors", {
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      if (!res.ok) return;
      const data = await res.json();

      const tbody = document.getElementById("admin-doctors-tbody");
      tbody.innerHTML = "";

      this.doctors = (data.doctors || []).sort((a, b) => a.name.localeCompare(b.name));
      this.doctors.forEach(doc => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-100 hover:bg-blue-50/40 text-sm";
        tr.innerHTML = `
          <td class="py-3 px-4 font-bold text-[#1e1b4b]">${doc.name}</td>
          <td class="py-3 px-4 text-[#0084ff] font-bold">${doc.department}</td>
          <td class="py-3 px-4 text-slate-600 text-xs">${doc.specialization}</td>
          <td class="py-3 px-4 text-slate-600 font-mono text-xs font-bold">${doc.room_number}</td>
          <td class="py-3 px-4 text-xs font-mono font-semibold text-slate-700">${doc.booked_slots} / ${doc.total_slots} booked</td>
          <td class="py-3 px-4">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold ${doc.is_active ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-slate-100 text-slate-600 border border-slate-200'}">
              ${doc.is_active ? 'Active' : 'Inactive'}
            </span>
          </td>
          <td class="py-3 px-4 text-right space-x-1.5 whitespace-nowrap">
            <button onclick="window.adminPortal.openEditModal(${doc.id})" class="px-3 py-1 rounded-full bg-blue-50 hover:bg-blue-100 text-[#0084ff] text-xs font-bold border border-blue-200 transition shadow-sm">
              Edit
            </button>
            <button onclick="window.adminPortal.toggleDoctor(${doc.id})" class="px-3 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold border border-slate-300 transition">
              ${doc.is_active ? 'Deactivate' : 'Activate'}
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error("Doctors load error:", err);
    }
  }

  openEditModal(docId) {
    const doc = (this.doctors || []).find(d => d.id === docId);
    if (!doc) return;

    document.getElementById("edit-doc-id").value = doc.id;
    document.getElementById("edit-doc-name").value = doc.name;
    document.getElementById("edit-doc-dept").value = doc.department;
    document.getElementById("edit-doc-spec").value = doc.specialization;
    document.getElementById("edit-doc-room").value = doc.room_number;

    const unbooked = Math.max(0, doc.total_slots - doc.booked_slots);
    document.getElementById("edit-doc-slots").value = unbooked;
    document.getElementById("edit-doc-add-slots").value = "0";

    const activeSelect = document.getElementById("edit-doc-active");
    if (activeSelect) activeSelect.value = doc.is_active ? "true" : "false";

    const slotSummary = document.getElementById("edit-doc-slot-summary");
    if (slotSummary) {
      slotSummary.innerText = `Currently: ${doc.booked_slots} booked, ${unbooked} available (${doc.total_slots} total)`;
    }

    document.getElementById("edit-doctor-modal").classList.remove("hidden");
  }

  async saveDoctorEdit() {
    const docId = document.getElementById("edit-doc-id").value;
    const name = document.getElementById("edit-doc-name").value.trim();
    const department = document.getElementById("edit-doc-dept").value.trim();
    const specialization = document.getElementById("edit-doc-spec").value.trim();
    const roomNumber = document.getElementById("edit-doc-room").value.trim();
    const availableSlots = parseInt(document.getElementById("edit-doc-slots").value, 10);
    const addSlots = parseInt(document.getElementById("edit-doc-add-slots").value, 10);
    const isActive = document.getElementById("edit-doc-active").value === "true";

    if (!docId || !name || !roomNumber) {
      alert("Please provide valid Doctor Name and Room Number.");
      return;
    }

    try {
      const payload = {
        name,
        department,
        specialization,
        room_number: roomNumber,
        is_active: isActive
      };
      if (!isNaN(availableSlots)) {
        payload.available_slots_count = availableSlots;
      }
      if (!isNaN(addSlots) && addSlots > 0) {
        payload.add_slots = addSlots;
      }

      const res = await fetch(`/api/admin/doctors/${docId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update physician.");
      }

      document.getElementById("edit-doctor-modal").classList.add("hidden");
      await this.loadDashboard();
    } catch (e) {
      alert("Error updating physician: " + e.message);
    }
  }

  async toggleDoctor(docId) {
    try {
      await fetch(`/api/admin/doctors/${docId}/toggle-active`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      this.loadDoctors();
    } catch (e) {
      alert("Toggle doctor failed: " + e.message);
    }
  }

  async createDoctor() {
    const name = document.getElementById("new-doc-name").value;
    const email = document.getElementById("new-doc-email").value;
    const department = document.getElementById("new-doc-dept").value;
    const specialization = document.getElementById("new-doc-spec").value;
    const roomNumber = document.getElementById("new-doc-room").value;

    if (!name || !email || !department) {
      alert("Please fill in Doctor Name, Email, and Department.");
      return;
    }

    try {
      const res = await fetch("/api/admin/doctors", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.token}`
        },
        body: JSON.stringify({
          name,
          email,
          department,
          specialization: specialization || "General Specialist",
          room_number: roomNumber || "OPD-201",
          password: "doctor123"
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Doctor creation failed.");
      }

      alert("Doctor authorized and initial slots generated!");
      document.getElementById("create-doctor-modal").classList.add("hidden");
      this.loadDoctors();
    } catch (err) {
      alert(err.message);
    }
  }

  async loadAuditLogs() {
    try {
      const res = await fetch("/api/admin/audit-logs?limit=50", {
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      if (!res.ok) return;
      const data = await res.json();

      const tbody = document.getElementById("admin-audit-tbody");
      tbody.innerHTML = "";

      data.logs.forEach(log => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-100 hover:bg-blue-50/30 text-xs font-mono";

        const isEmergency = log.event_type.includes("RED_FLAG") || log.event_type.includes("EMERGENCY");
        const eventBadge = isEmergency
          ? `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700 border border-rose-300 animate-pulse">${log.event_type}</span>`
          : `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-[#0084ff] border border-blue-200">${log.event_type}</span>`;

        tr.innerHTML = `
          <td class="py-2.5 px-3 text-slate-500 font-semibold">#${log.id}</td>
          <td class="py-2.5 px-3">${eventBadge}</td>
          <td class="py-2.5 px-3 text-slate-700 font-semibold">${log.call_id || 'SYSTEM'}</td>
          <td class="py-2.5 px-3 text-slate-700 font-sans truncate max-w-xs" title="${log.payload}">${log.payload}</td>
          <td class="py-2.5 px-3 text-slate-400 truncate max-w-[100px]" title="${log.prev_hash}">${log.prev_hash.substring(0, 10)}...</td>
          <td class="py-2.5 px-3 text-[#0084ff] font-bold truncate max-w-[100px]" title="${log.record_hash}">${log.record_hash.substring(0, 10)}...</td>
          <td class="py-2.5 px-3 text-slate-500">${new Date(log.timestamp).toLocaleTimeString()}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error("Audit log load error:", err);
    }
  }

  async verifyAuditChain() {
    const banner = document.getElementById("audit-verify-result");
    banner.innerHTML = `<span class="inline-block w-2.5 h-2.5 rounded-full bg-[#0084ff] animate-spin mr-2"></span>Computing SHA-256 hashes sequentially across entire audit ledger...`;
    banner.classList.remove("hidden");

    try {
      const res = await fetch("/api/admin/audit-logs/verify", {
        headers: { "Authorization": `Bearer ${this.token}` }
      });
      const data = await res.json();

      if (data.is_valid) {
        banner.className = "p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs flex items-center space-x-2 shadow-sm";
        banner.innerHTML = `
          <svg class="w-5 h-5 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          <div>
            <strong class="text-emerald-900 block font-bold">✓ CRYPTOGRAPHIC AUDIT INTEGRITY VERIFIED (SHA-256)</strong>
            <span>All ${data.total_records} records verified. Zero tampering detected. Chain root to head is unbroken.</span>
          </div>
        `;
      } else {
        banner.className = "p-4 rounded-2xl bg-rose-50 border border-rose-300 text-rose-800 text-xs flex items-center space-x-2 shadow-sm";
        banner.innerHTML = `
          <svg class="w-5 h-5 text-rose-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <div>
            <strong class="text-rose-900 block font-bold">⚠️ CHAIN VERIFICATION FAILED</strong>
            <span>${data.details} (Broken at record #${data.broken_at_id})</span>
          </div>
        `;
      }
    } catch (e) {
      banner.innerHTML = `<span class="text-rose-400">Verification request error: ${e.message}</span>`;
    }
  }
}

window.adminPortal = new AdminPortal();
