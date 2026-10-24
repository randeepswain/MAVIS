// MAVIS Main Application Router & Authentication Controller

class MavisApp {
  constructor() {
    this.currentView = "home"; // home, voice, patient, doctor, admin
    this.token = localStorage.getItem("mavis_token") || null;
    this.user = JSON.parse(localStorage.getItem("mavis_user") || "null");
    this.role = localStorage.getItem("mavis_role") || (this.token && this.user ? this.user.role : null);
  }

  init() {
    this.setupNavigation();

    // Check if initial URL has appointment token query parameter
    const urlParams = new URLSearchParams(window.location.search);
    const tokenQuery = urlParams.get("token");

    if (tokenQuery) {
      // Direct token tracking link: opt into patient role, show app, track token
      this.role = "patient";
      localStorage.setItem("mavis_role", "patient");
      this.showMainApp();
      this.applyRoleNavVisibility();
      this.updateAuthUI();
      this.switchView("patient");
      const input = document.getElementById("patient-token-input");
      if (input) input.value = tokenQuery;
      if (window.patientPortal) {
        window.patientPortal.trackToken(tokenQuery);
      }
      return;
    }

    // Default Root Route:
    // If no active session or role, show Standalone LoginPage as the default first screen
    if (!this.token && !this.role) {
      this.showLoginPage();
    } else {
      this.showMainApp();
      this.applyRoleNavVisibility();
      this.updateAuthUI();

      if (this.role === "patient") {
        this.switchView("home");
      } else if (this.user && this.user.role === "ADMIN") {
        this.switchView("admin");
      } else if (this.user && this.user.role === "DOCTOR") {
        this.switchView("doctor");
      } else {
        this.switchView("home");
      }
    }
  }

  setupNavigation() {
    const navItems = ["home", "voice", "patient", "doctor", "admin"];
    navItems.forEach(view => {
      const btn = document.getElementById(`nav-${view}`);
      if (btn) {
        btn.addEventListener("click", () => this.switchView(view));
      }
      const mobileBtn = document.getElementById(`mobile-nav-${view}`);
      if (mobileBtn) {
        mobileBtn.addEventListener("click", () => this.switchView(view));
      }
    });

    const logoutBtn = document.getElementById("nav-logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", () => this.handleLogout());
    }
    const mobileLogoutBtn = document.getElementById("mobile-nav-logout");
    if (mobileLogoutBtn) {
      mobileLogoutBtn.addEventListener("click", () => this.handleLogout());
    }
  }

  showLoginPage() {
    const viewLogin = document.getElementById("view-login");
    const appContainer = document.getElementById("app-container");
    if (viewLogin) viewLogin.classList.remove("hidden");
    if (appContainer) appContainer.classList.add("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  showMainApp() {
    const viewLogin = document.getElementById("view-login");
    const appContainer = document.getElementById("app-container");
    if (viewLogin) viewLogin.classList.add("hidden");
    if (appContainer) appContainer.classList.remove("hidden");
  }

  enterAsPatient() {
    this.role = "patient";
    this.token = null;
    this.user = null;
    localStorage.setItem("mavis_role", "patient");
    localStorage.removeItem("mavis_token");
    localStorage.removeItem("mavis_user");

    // Secure Transition to Main Application Interface
    this.showMainApp();
    this.applyRoleNavVisibility();
    this.updateAuthUI();
    this.switchView("home");
  }

  async handleLogin() {
    const emailInput = document.getElementById("login-email");
    const passwordInput = document.getElementById("login-password");
    if (!emailInput || !passwordInput) return;

    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Authentication failed. Please check credentials.");
      }

      const data = await res.json();
      this.token = data.access_token;
      this.user = {
        email: data.email,
        full_name: data.full_name,
        role: data.role,
        doctor_id: data.doctor_id,
        department: data.department
      };
      this.role = data.role;

      localStorage.setItem("mavis_token", this.token);
      localStorage.setItem("mavis_user", JSON.stringify(this.user));
      localStorage.setItem("mavis_role", this.role);

      // Secure Redirect from Standalone LoginPage to Main Application Interface
      this.showMainApp();
      this.applyRoleNavVisibility();
      this.updateAuthUI();

      if (this.role === "ADMIN") {
        this.switchView("admin");
      } else {
        this.switchView("doctor");
      }
    } catch (err) {
      alert("Authentication Error: " + err.message);
    }
  }

  handleLogout() {
    this.token = null;
    this.user = null;
    this.role = null;
    localStorage.removeItem("mavis_token");
    localStorage.removeItem("mavis_user");
    localStorage.removeItem("mavis_role");

    // Reset URL if search params present
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", "/");
    }

    // Terminate session and redirect back to Standalone LoginPage
    this.showLoginPage();
  }

  applyRoleNavVisibility() {
    const navHome = document.getElementById("nav-home");
    const navVoice = document.getElementById("nav-voice");
    const navPatient = document.getElementById("nav-patient");
    const navDoctor = document.getElementById("nav-doctor");
    const navAdmin = document.getElementById("nav-admin");
    const navLogout = document.getElementById("nav-logout-btn");

    const mobileNavHome = document.getElementById("mobile-nav-home");
    const mobileNavVoice = document.getElementById("mobile-nav-voice");
    const mobileNavPatient = document.getElementById("mobile-nav-patient");
    const mobileNavDoctor = document.getElementById("mobile-nav-doctor");
    const mobileNavAdmin = document.getElementById("mobile-nav-admin");
    const mobileNavLogout = document.getElementById("mobile-nav-logout");

    // Home and Logout are always available in main app
    if (navHome) navHome.classList.remove("hidden");
    if (mobileNavHome) mobileNavHome.classList.remove("hidden");
    if (navLogout) navLogout.classList.remove("hidden");
    if (mobileNavLogout) mobileNavLogout.classList.remove("hidden");

    if (this.role === "patient") {
      // Patient Role: 3 tabs (Home, Voice Intake, Patient Portal)
      // HIDE Doctor Portal and Admin tabs
      if (navVoice) navVoice.classList.remove("hidden");
      if (navPatient) navPatient.classList.remove("hidden");
      if (mobileNavVoice) mobileNavVoice.classList.remove("hidden");
      if (mobileNavPatient) mobileNavPatient.classList.remove("hidden");

      if (navDoctor) navDoctor.classList.add("hidden");
      if (navAdmin) navAdmin.classList.add("hidden");
      if (mobileNavDoctor) mobileNavDoctor.classList.add("hidden");
      if (mobileNavAdmin) mobileNavAdmin.classList.add("hidden");
    } else if (this.token && this.user) {
      if (this.user.role === "DOCTOR") {
        // Doctor Role / Doctor Portal: REMOVE Patient Portal and Voice Intake from Navbar!
        if (navVoice) navVoice.classList.add("hidden");
        if (navPatient) navPatient.classList.add("hidden");
        if (mobileNavVoice) mobileNavVoice.classList.add("hidden");
        if (mobileNavPatient) mobileNavPatient.classList.add("hidden");

        if (navDoctor) navDoctor.classList.remove("hidden");
        if (navAdmin) navAdmin.classList.add("hidden");
        if (mobileNavDoctor) mobileNavDoctor.classList.remove("hidden");
        if (mobileNavAdmin) mobileNavAdmin.classList.add("hidden");
      } else if (this.user.role === "ADMIN") {
        // Admin Role: Only Home, Admin & Audit, Logout. HIDE Doctor Portal, Patient Portal, and Voice Intake!
        if (navVoice) navVoice.classList.add("hidden");
        if (navPatient) navPatient.classList.add("hidden");
        if (mobileNavVoice) mobileNavVoice.classList.add("hidden");
        if (mobileNavPatient) mobileNavPatient.classList.add("hidden");

        if (navDoctor) navDoctor.classList.add("hidden");
        if (navAdmin) navAdmin.classList.remove("hidden");
        if (mobileNavDoctor) mobileNavDoctor.classList.add("hidden");
        if (mobileNavAdmin) mobileNavAdmin.classList.remove("hidden");
      }
    } else {
      // No credentials / default fallback
      if (navVoice) navVoice.classList.remove("hidden");
      if (navPatient) navPatient.classList.remove("hidden");
      if (mobileNavVoice) mobileNavVoice.classList.remove("hidden");
      if (mobileNavPatient) mobileNavPatient.classList.remove("hidden");

      if (navDoctor) navDoctor.classList.add("hidden");
      if (navAdmin) navAdmin.classList.add("hidden");
      if (mobileNavDoctor) mobileNavDoctor.classList.add("hidden");
      if (mobileNavAdmin) mobileNavAdmin.classList.add("hidden");
    }
  }

  updateAuthUI() {
    this.applyRoleNavVisibility();

    const userBox = document.getElementById("auth-user-info");
    if (userBox) {
      if (this.token && this.user) {
        userBox.classList.remove("hidden");
        userBox.innerHTML = `
          <div class="flex items-center space-x-1.5">
            <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span class="font-bold text-[#1e1b4b]">${this.user.full_name}</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-[#0084ff] font-bold font-mono border border-blue-200">${this.user.role}</span>
          </div>
        `;
      } else {
        userBox.classList.add("hidden");
        userBox.innerHTML = "";
      }
    }
  }

  switchView(viewName) {
    // Auth protection for staff views
    if (viewName === "doctor") {
      if (!this.token || (this.user?.role !== "DOCTOR" && this.user?.role !== "ADMIN")) {
        alert("Medical staff credentials required. Please authenticate via the Login Gateway.");
        this.showLoginPage();
        return;
      }
      if (window.doctorPortal) {
        window.doctorPortal.setToken(this.token);
        window.doctorPortal.loadDashboard();
      }
    } else if (viewName === "admin") {
      if (!this.token || this.user?.role !== "ADMIN") {
        alert("Administrative credentials required. Please authenticate via the Login Gateway.");
        this.showLoginPage();
        return;
      }
      if (window.adminPortal) {
        window.adminPortal.setToken(this.token);
        window.adminPortal.loadDashboard();
      }
    }

    this.currentView = viewName;
    const views = ["home", "voice", "patient", "doctor", "admin"];

    // Switch visible main application view section
    views.forEach(v => {
      const el = document.getElementById(`view-${v}`);
      const btn = document.getElementById(`nav-${v}`);
      if (el) el.classList.toggle("hidden", v !== viewName);
      if (btn) {
        if (v === viewName) {
          btn.classList.add("text-[#0084ff]", "border-b-2", "border-[#0084ff]");
          btn.classList.remove("text-slate-600");
        } else {
          btn.classList.remove("text-[#0084ff]", "border-b-2", "border-[#0084ff]");
          btn.classList.add("text-slate-600");
        }
      }
    });

    // Mobile nav buttons sync
    views.forEach(v => {
      const mBtn = document.getElementById(`mobile-nav-${v}`);
      if (mBtn) {
        if (v === viewName) {
          mBtn.classList.add("text-[#0084ff]", "font-bold");
          mBtn.classList.remove("text-slate-600", "font-medium");
        } else {
          mBtn.classList.remove("text-[#0084ff]", "font-bold");
          mBtn.classList.add("text-slate-600", "font-medium");
        }
      }
    });

    // Re-verify role nav visibility
    this.applyRoleNavVisibility();

    // Scroll to top on view change
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  renderCurrentView() {
    this.switchView(this.currentView);
  }
}

// Global helper for 1-click tracking from voice booking card
window.loadTokenInTracker = function(tokenId) {
  if (window.mavisApp) {
    window.mavisApp.showMainApp();
    window.mavisApp.role = "patient";
    localStorage.setItem("mavis_role", "patient");
    window.mavisApp.applyRoleNavVisibility();
    window.mavisApp.switchView("patient");
  }
  const input = document.getElementById("patient-token-input");
  if (input) input.value = tokenId;
  if (window.patientPortal) {
    window.patientPortal.trackToken(tokenId);
  }
};

window.mavisApp = new MavisApp();
document.addEventListener("DOMContentLoaded", () => {
  window.mavisApp.init();
});
