# 🏥 MAVIS — Multi-Agent Voice Intake System
### Autonomous Voice AI Hospital Management & Deterministic Scheduling Platform
**M. S. Ramaiah University of Applied Sciences, Bengaluru**  
*Faculty of Engineering and Technology — Department of Computer Science & Engineering*  
**Project Batch No. 45**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://www.langchain.com/langgraph)
[![SQLite WAL](https://img.shields.io/badge/Database-SQLite%20WAL%20%2F%20PostgreSQL-blue.svg)](https://www.sqlite.org/wal.html)
[![Tests Passing](https://img.shields.io/badge/Tests-6%2F6%20Passing-brightgreen.svg)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 👥 Project Contributors
- **Sakshi Srivastava** (`23ETIS411047`)
- **Randeep Swain** (`23ETIS411041`)
- **Vyshnav Vinod PP** (`23ETIS411055`)
- **Sridarsh Anand** (`23ETCS002135`)
- **Faculty Guide**: Dr. Sasireka V, Assistant Professor, Dept. of CSE

---

## 📑 Table of Contents
1. [🌟 What is MAVIS? (In Simple Terms)](#-what-is-mavis-in-simple-terms)
2. [⚡ Quickstart (Run in 3 Commands)](#-quickstart-run-in-3-commands)
3. [🚀 Beginner's Step-by-Step Installation Guide](#-beginners-step-by-step-installation-guide)
   - [Prerequisites](#prerequisites)
   - [Step 1: Clone the Repository](#step-1-clone-the-repository)
   - [Step 2: Create a Virtual Environment](#step-2-create-a-virtual-environment)
   - [Step 3: Install Required Packages](#step-3-install-required-packages)
   - [Step 4: Configure Environment Variables (Optional)](#step-4-configure-environment-variables-optional)
   - [Step 5: Launch the MAVIS Server](#step-5-launch-the-mavis-server)
   - [Step 6: Open the Web Portal](#step-6-open-the-web-portal)
   - [Step 7: Run Automated Tests](#step-7-run-automated-tests)
4. [🏗️ System Architecture & How It Works](#️-system-architecture--how-it-works)
5. [🎮 Interactive Walkthrough: How to Test Each Feature](#-interactive-walkthrough-how-to-test-each-feature)
   - [1. Voice AI Intake Simulator](#1-voice-ai-intake-simulator-tab)
   - [2. Patient Portal & Token Tracking](#2-patient-portal-tab)
   - [3. Doctor Portal & AI Clinical Handoff](#3-doctor-portal-tab)
   - [4. Admin Portal & Cryptographic Hash Audit](#4-admin-portal--tamper-evident-audit-tab)
6. [🔑 Pre-Seeded Demo Accounts & Sample Tokens](#-pre-seeded-demo-accounts--sample-tokens)
7. [📡 API Endpoints & Interactive Documentation](#-api-endpoints--interactive-documentation)
8. [📂 Project Directory Structure](#-project-directory-structure)
9. [🛠️ Tech Stack & Engineering Rationale](#️-tech-stack--engineering-rationale)
10. [❓ Troubleshooting & FAQ](#-troubleshooting--faq)
11. [📤 Pushing Changes to GitHub](#-pushing-changes-to-github)

---

## 🌟 What is MAVIS? (In Simple Terms)

When patients call a hospital call center during busy hours, they are often placed on long hold times. If a patient is experiencing life-threatening symptoms (such as a heart attack, anaphylaxis, or stroke), delays can be catastrophic. Furthermore, manual phone triage often results in routing mistakes, accidental double-booked doctor appointments, and illegible or incomplete clinical notes.

**MAVIS (Multi-Agent Voice Intake System)** is an autonomous, full-stack hospital voice AI platform designed to eliminate these problems:

1. **Answers & Speaks Automatically**: Answers incoming patient phone calls or browser audio streams in real time with high naturalness and sub-second speech turnaround.
2. **Deterministic Emergency Safety Gate (F4)**: Runs zero-latency regex matching on every speech fragment *before* any language model. If red-flag symptoms (chest pain, stroke signs, severe hemorrhage) are detected, scheduling is immediately halted and the call is routed to a human emergency nurse with automated fallback to emergency lines (**112 / 108**).
3. **Clinical Symptom Triage (F1)**: An intelligent state-machine agent listens to symptoms, queries a clinical knowledge base (RAG), maps the complaint to the correct medical specialty (Cardiology, Neurology, Orthopedics, etc.), and asks clarifying questions when needed.
4. **Deterministic Zero Double-Booking Engine (F2)**: Uses a 3-tier concurrency defense (180-second Redis soft-holds, database row-locking `SELECT ... FOR UPDATE`, and composite unique constraints) to guarantee **zero double-bookings**, even under simultaneous heavy call loads.
5. **AI Clinical Handoff Brief (F3)**: Synthesizes a structured medical brief (Chief Complaint, Urgency, Differential Possibilities, Recommended Workup) and delivers it directly to the doctor's dashboard before the consultation starts.
6. **Automated Follow-Up Agent (F5)**: Proactively monitors patient recovery post-consultation and alerts medical staff if red flags arise.
7. **Tamper-Evident SHA-256 Audit Ledger**: Chained cryptographic hashing guarantees that every scheduling action and emergency trigger is permanently verifiable and tamper-evident.

---

## ⚡ Quickstart (Run in 3 Commands)

If you already have Python 3.10+ installed and a terminal open in the project folder:

```bash
# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1       # On Windows PowerShell (or: source venv/bin/activate on Mac/Linux)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open your browser to **[http://127.0.0.1:8000](http://127.0.0.1:8000)**!

---

## 🚀 Beginner's Step-by-Step Installation Guide

Follow these simple instructions to set up and run MAVIS on your computer.

### Prerequisites

Before starting, ensure you have:
1. **Python 3.10, 3.11, 3.12, or 3.13** installed.
   - Check by running: `python --version` (or `python3 --version`).
   - If not installed, download from [python.org/downloads](https://www.python.org/downloads/).
   - ⚠️ **Important on Windows**: During installation, check the box that says **"Add Python to PATH"**.
2. **Git** installed.
   - Check by running: `git --version`.
   - If not installed, download from [git-scm.com](https://git-scm.com/).

---

### Step 1: Clone the Repository

Open your terminal or command prompt and clone the repository:

```bash
git clone https://github.com/randeepswain/MAVIS.git
cd MAVIS
```

*(If you already have the folder downloaded locally, simply open a terminal inside the `MAVIS` folder).*

---

### Step 2: Create a Virtual Environment

A virtual environment isolates project packages so they do not conflict with other Python installations on your computer.

#### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> 💡 **PowerShell Execution Policy Tip**:  
> If PowerShell gives an error saying `running scripts is disabled on this system`, run this command once:  
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`  
> Then re-run `.\venv\Scripts\Activate.ps1`.

#### On Windows (Command Prompt `cmd.exe`):
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

#### On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

*(When active, you will see `(venv)` at the beginning of your terminal line).*

---

### Step 3: Install Required Packages

Install all required Python packages with a single command:

```bash
pip install -r requirements.txt
```

This installs:
- **FastAPI** & **Uvicorn**: Async high-performance web server & REST/WebSocket APIs.
- **SQLAlchemy 2.0** & **aiosqlite**: Async database engine with Write-Ahead Logging (WAL).
- **LangGraph** & **LangChain-Core**: Multi-agent cyclical state machine.
- **Pydantic**: Robust data validation and settings schemas.
- **Redis**: In-memory caching and slot-locking client (with built-in fallback).
- **PyJWT** & **Cryptography**: Secure token-based authentication.
- **Pytest** & **pytest-asyncio**: Automated concurrency and safety test suite.

---

### Step 4: Configure Environment Variables (Optional)

MAVIS is designed with **zero-setup defaults**—it runs immediately out-of-the-box using local SQLite with Write-Ahead Logging (WAL) and an in-memory Redis fallback.

If you wish to customize keys or use Groq LLM:
1. Make a copy of `.env.example` named `.env`:
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env

   # Mac / Linux
   cp .env.example .env
   ```
2. (Optional) Add your free Groq API key in `.env` to enable online Llama-3 neural extraction:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```
   *(If left blank, MAVIS automatically runs its deterministic clinical heuristic extractor, which works completely offline!)*

---

### Step 5: Launch the MAVIS Server

Start the Uvicorn application server:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

You will see terminal output showing:
```
INFO:     Started server process
2026-10-24 [INFO] mavis.main: Starting MAVIS backend...
2026-10-24 [INFO] mavis.session: SQLite WAL mode enabled successfully.
2026-10-24 [INFO] mavis.seed: Seeding initial hospital data (Doctors, Slots, Tokens)...
2026-10-24 [INFO] mavis.seed: Seed database execution complete.
2026-10-24 [INFO] mavis.main: MAVIS backend initialization complete. Ready for telephony and web portal traffic.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

### Step 6: Open the Web Portal

Open your web browser (Chrome, Edge, Firefox, or Safari) and navigate to:

👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

You will be greeted by the **MAVIS Unified Hospital Management Portal** featuring four tabs:
1. `🎙️ Voice AI Intake` — Real-time voice simulation with audio visualizer, barge-in detection, and emergency triggers.
2. `🎫 Patient Portal` — Public queue status tracker and appointment token lookup.
3. `🩺 Doctor Portal` — Authenticated dashboard with patient queue, AI Clinical Handoff Briefs, and follow-up tools.
4. `🛡️ Admin & Audit` — Operational telemetry metrics, doctor management, and cryptographic SHA-256 audit log verifier.

---

### Step 7: Run Automated Tests

To verify system integrity, open a new terminal window, activate the virtual environment, and run:

```bash
python -m pytest tests -v
```

All 6 test suites will pass:
```
tests/test_concurrency.py::test_concurrent_slot_bookings_zero_double_bookings PASSED [ 16%]
tests/test_concurrency.py::test_idempotency_on_dropped_call_reconnect PASSED         [ 33%]
tests/test_langgraph.py::test_multi_agent_graph_transitions PASSED                   [ 50%]
tests/test_langgraph.py::test_clarification_and_handoff_brief PASSED                 [ 66%]
tests/test_safety_gate.py::test_safety_gate_triggers PASSED                          [ 83%]
tests/test_safety_gate.py::test_hash_chained_audit_log_tamper_evidence PASSED       [100%]
================================ 6 passed in 6.23s =================================
```

---

## 🏗️ System Architecture & How It Works

MAVIS is built as a robust 4-layer architecture separating telephony audio, multi-agent medical triage, deterministic ACID database concurrency, and presentation:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAYER 1: AUDIO & TELEPHONY                            │
│  [ WebRTC / SIP Inbound Call ] ──▶ [ Silero VAD (Barge-in Detection) ]     │
│             ▲                                    │                          │
│             │                                    ▼                          │
│     [ Piper TTS Voice ] ◀────────── [ Faster-Whisper ASR (Speech-to-Text) ] │
└──────────────────────────────────────────────┬──────────────────────────────┘
                                               │ Live Transcription Stream
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 LAYER 2: LANGGRAPH MULTI-AGENT STATE MACHINE                │
│                                                                             │
│                  ┌────────────────────────────────────────┐                 │
│                  │  🚨 Safety Gate Filter (Regex / Rule)  │                 │
│                  └───────────────────┬────────────────────┘                 │
│                         Safe?        │        Emergency Detected!           │
│                ┌─────────────────────┴────────────────────┐                 │
│                ▼                                          ▼                 │
│  ┌───────────────────────────┐         ┌──────────────────────────────────┐ │
│  │ Clinical Triage (F1 Agent)│         │ Emergency Red-Flag Bypass (F4)   │ │
│  │ - Symptom Extraction      │         │ - Terminate automated call       │ │
│  │ - RAG Department Matching │         │ - Bridge to Triage Nurse         │ │
│  │ - Clarification Cycle     │         │ - Fallback: 112 / 108            │ │
│  └─────────────┬─────────────┘         └──────────────────────────────────┘ │
│                ▼                                                            │
│  ┌───────────────────────────┐         ┌──────────────────────────────────┐ │
│  │ Doctor Handoff (F3 Agent) │         │ Automated Follow-Up (F5 Agent)   │ │
│  │ - Structured SBAR Brief   │         │ - Post-visit health recovery     │ │
│  └───────────────────────────┘         └──────────────────────────────────┘ │
└──────────────────────────────────────────────┬──────────────────────────────┘
                                               │ Validated Booking Request
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 LAYER 3: DETERMINISTIC CONCURRENCY & STORAGE                │
│                                                                             │
│  1. Redis Soft-Hold: Atomic SETNX with 180s TTL (hold:slot:{id})             │
│  2. SQLite WAL / PostgreSQL: SELECT ... FOR UPDATE Row-Level Locking        │
│  3. Database Schema: UNIQUE(doctor_id, slot_timestamp) Constraint          │
│  4. Tamper-Evident Ledger: SHA-256 Hash Chaining: H_n = SHA256(H_{n-1} + D) │
└──────────────────────────────────────────────┬──────────────────────────────┘
                                               │ REST API / WebSocket
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LAYER 4: UNIFIED WEB PORTAL                           │
│   [ 🎙️ Voice Intake ]  [ 🎫 Patient View ]  [ 🩺 Doctor ]  [ 🛡️ Admin/Audit ] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎮 Interactive Walkthrough: How to Test Each Feature

### 1. Voice AI Intake Simulator (`🎙️ Voice AI Intake` tab)

1. Click **"Connect Live Voice Call"**.
   - The waveform visualizer starts animating.
   - You will hear the receptionist greet:  
     *"Hello, welcome to MAVIS Hospital Intake. This call is transcribed for medical coordination. Do you consent to proceed with automated clinical triage and scheduling?"*
2. **Test Emergency Red-Flag Bypass (F4)**:
   - Click the preset scenario: **"🚨 Cardiac: Crushing chest pain radiating to left arm"**.
   - **Result**: The agent instantly cuts off scheduling, flags a critical cardiac emergency, and displays an emergency bridge card to Human Nurse Desk (`+91-80-2360-1234`) with emergency numbers (`112` / `108`), appending a cryptographic SHA-256 hash record.
3. **Test Conversational Appointment Booking**:
   - Reconnect call.
   - Click **"1. Yes, I consent"**.
   - Click **"2. Orthopedics (Knee Pain)"** (*"I have severe knee pain and swelling for 3 days after playing football, pain scale 7 out of 10"*).
   - **Result**: Triage evaluates urgency, selects Orthopedics department, queries doctor availability, reserves the slot with Dr. Anita Desai, and presents a green confirmation card with a Token ID (e.g., `ORTH-20261020-002`).
4. **Test Barge-In / Interruption**:
   - While the agent is speaking, click **"⚡ Trigger Barge-in"**.
   - **Result**: The agent's speech pauses immediately, simulating real-time human voice interruption.

---

### 2. Patient Portal (`🎫 Patient Portal` tab)

1. Navigate to the **Patient Portal** tab (accessible publicly without login).
2. Enter any Token ID, for example: `CARD-20261020-001` or `ORTH-20261020-001`.
3. Click **"Check Status →"**.
4. You will see:
   - Live queue position (e.g., `#1`, `0 patients ahead`).
   - Assigned Doctor (`Dr. Priya Sharma`) & Room (`OPD-101`).
   - Scheduled Time Slot.
   - Status (`IN_QUEUE`, `IN_CONSULTATION`, or `COMPLETED`).
   - The card automatically polls every 10 seconds for real-time queue movement!

---

### 3. Doctor Portal (`🩺 Doctor Portal` tab)

1. Click the **"Staff Login"** button in the top navigation bar.
2. Click the quick-fill button **"Doctor (Cardiology)"** (`priya.sharma@mavis.hospital` / `doctor123`).
3. Click **"Authenticate with JWT →"**.
4. Inside the Doctor Dashboard:
   - View your active patient queue for today.
   - Click **"View AI Brief"** to inspect the AI Clinical Handoff Brief showing: Chief Complaint, Triage Reasoning, Urgency, and Recommended Clinical Workup (e.g. 12-lead ECG, troponin markers).
   - Click **"Call"** to move the patient to `IN_CONSULTATION`.
   - Click **"Done"** to complete the consultation.
   - Click **"Follow-Up"** to test the F5 automated patient recovery check.

---

### 4. Admin Portal & Tamper-Evident Audit (`🛡️ Admin & Audit` tab)

1. Log in using the **"Hospital Admin"** quick-fill button (`admin@mavis.hospital` / `admin123`).
2. Navigate to **"🛡️ Admin & Audit"**.
3. View operational metrics:
   - Call completion rate (94.2%)
   - Slot utilization percentage
   - Under-triage rate (<0.1%)
   - Emergency triggers caught
4. **Test SHA-256 Hash Chain Integrity**:
   - Scroll to the **Cryptographic Tamper-Evident Audit Ledger**.
   - Click **"Verify SHA-256 Chain Integrity"**.
   - The engine iterates through every record from genesis hash (`0000...`) to the head hash, recalculates the cryptographic hashes, and shows:
     *"✓ CRYPTOGRAPHIC AUDIT INTEGRITY VERIFIED (SHA-256) - All records verified. Zero tampering detected."*

---

## 🔑 Pre-Seeded Demo Accounts & Sample Tokens

### Ready Staff Credentials
| Portal | Role | Email Address | Password | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Doctor Portal** | `DOCTOR` | `priya.sharma@mavis.hospital` | `doctor123` | View Cardiology queue, inspect AI Handoff Briefs, update consultation state, initiate follow-ups. |
| **Doctor Portal** | `DOCTOR` | `rajesh.kumar@mavis.hospital` | `doctor123` | View Neurology queue and patient handoff briefs. |
| **Admin Portal** | `ADMIN` | `admin@mavis.hospital` | `admin123` | Operational metrics, view all audit records, verify cryptographic hash chain. |
| **Patient Portal** | `PATIENT` | *Public Access* | *None* | Lookup appointment status and queue position using Token ID. |

### Ready Sample Tokens (Patient Portal)
- `CARD-20261020-001` (Cardiology • Patient: Aarav Mehta • Dr. Priya Sharma)
- `NEUR-20261020-001` (Neurology • Patient: Meera Sen • Dr. Rajesh Kumar)
- `ORTH-20261020-001` (Orthopedics • Patient: Rohan Gupta • Dr. Anita Desai)

---

## 📡 API Endpoints & Interactive Documentation

Once the server is running, you can explore and test all REST API endpoints using FastAPI's interactive Swagger UI:

- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### Key API Routes:
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Staff JWT authentication for Doctors & Admins |
| `GET` | `/api/scheduling/queue/{token_id}` | Public patient queue and appointment status |
| `GET` | `/api/scheduling/departments` | List hospital departments and available doctors |
| `POST` | `/api/scheduling/book` | Concurrency-protected slot reservation |
| `POST` | `/api/voice/session` | Start voice intake session |
| `POST` | `/api/voice/process-turn` | Process speech turn through LangGraph & Safety Gate |
| `GET` | `/api/doctor/queue` | Doctor's active patient queue |
| `GET` | `/api/doctor/brief/{token_id}` | Retrieve AI Clinical Handoff Brief |
| `POST` | `/api/doctor/status/{token_id}` | Update consultation status (`IN_CONSULTATION`, `COMPLETED`) |
| `GET` | `/api/admin/metrics` | Hospital telemetry and operational analytics |
| `GET` | `/api/admin/audit-logs` | Retrieve hash-chained audit records |
| `POST` | `/api/admin/audit/verify` | Cryptographically verify SHA-256 chain integrity |

---

## 📂 Project Directory Structure

```
MAVIS/
├── backend/
│   ├── agents/                     # LangGraph Multi-Agent Architecture
│   │   ├── graph.py                # Multi-agent state machine graph definition
│   │   ├── receptionist.py         # Initial greeting & patient consent agent
│   │   ├── safety_gate.py          # Deterministic zero-tolerance emergency filter
│   │   ├── triage_agent.py         # Clinical symptom extractor & RAG department routing
│   │   ├── handoff_agent.py        # Doctor clinical brief synthesizer (SBAR format)
│   │   └── follow_up_agent.py      # Automated post-visit patient recovery check
│   ├── api/                        # FastAPI REST API Routes
│   │   ├── auth.py                 # JWT authentication & role-based authorization
│   │   ├── scheduling_routes.py    # Public appointment booking & queue status
│   │   ├── doctor_routes.py        # Doctor dashboard & consultation workflow
│   │   ├── admin_routes.py         # Admin telemetry & SHA-256 audit ledger
│   │   └── voice.py                # Voice intake processing & audio pipeline API
│   ├── database/                   # Database Models & Session Management
│   │   ├── models.py               # SQLAlchemy models (Doctor, Slot, Token, Audit)
│   │   └── session.py              # Async SQLAlchemy engine with SQLite WAL
│   ├── services/                   # Business Logic & Infrastructure Services
│   │   ├── audio_pipeline.py       # Silero VAD, Faster-Whisper, Piper TTS integration
│   │   ├── audit.py                # Cryptographic SHA-256 linear hash-chain engine
│   │   ├── rag_service.py          # Medical knowledge base & vector matching
│   │   ├── redis_service.py        # Atomic 180s slot soft-holds (with in-memory fallback)
│   │   ├── scheduling.py           # Concurrency-safe slot allocation engine
│   │   └── seed_data.py            # Pre-seeded doctors, slots, tokens & genesis audit hash
│   ├── config.py                   # Central application settings & environment schema
│   └── main.py                     # FastAPI application entrypoint & static mounting
├── frontend/                       # Unified Web Portal (Zero Build Steps)
│   ├── css/
│   │   └── styles.css              # Modern glassmorphism clinical theme
│   ├── js/
│   │   ├── app.js                  # Main navigation, tab switching & login state
│   │   ├── voice_client.js         # Voice simulator, WebRTC audio & barge-in
│   │   ├── patient_portal.js       # Queue lookup & auto-polling
│   │   ├── doctor_portal.js        # Doctor queue, brief modal & consultation actions
│   │   └── admin_portal.js         # Telemetry charts & cryptographic verification
│   └── index.html                  # Single-page unified hospital portal
├── tests/                          # Automated Pytest Suite
│   ├── test_concurrency.py         # 100+ concurrent slot booking race condition tests
│   ├── test_langgraph.py           # Multi-agent graph state transitions & triage tests
│   └── test_safety_gate.py         # Emergency red-flag detection & SHA-256 tamper tests
├── .env.example                    # Template environment variables
├── .gitignore                      # Git exclusion rules
├── requirements.txt                # Python project dependencies
└── README.md                       # Complete documentation & beginner guide
```

---

## 🛠️ Tech Stack & Engineering Rationale

| Technology | Layer | Role in MAVIS | Why This Specific Tool Was Chosen |
| :--- | :--- | :--- | :--- |
| **Python 3.10+** | Core Language | Backend & AI logic | Rich ecosystem for asynchronous concurrency (`asyncio`), LangGraph, and medical NLP. |
| **FastAPI** | Backend Framework | Async Web API & WebSockets | High performance (based on Starlette & Pydantic), native async loop, auto OpenAPI docs. |
| **SQLAlchemy 2.0 (Async)** | Database ORM | Transactions & Models | ACID guarantees, row-level locking (`SELECT ... FOR UPDATE`), composite unique constraints. |
| **aiosqlite & asyncpg** | Database Drivers | SQLite & PostgreSQL engines | Zero-friction local startup with SQLite Write-Ahead Logging (WAL) and drop-in PostgreSQL support. |
| **Redis (with Fallback)** | Caching & Holds | 180s slot soft-holds | Atomic `SET NX EX` keys (`hold:slot:{id}`) temporarily reserve slots during active intake calls. |
| **LiveKit Gateway** | Layer 1 Telephony | WebRTC & SIP routing | Open-source real-time audio server connecting telephony trunks with ultra-low latency (<100ms). |
| **Silero VAD** | Layer 1 Audio | Voice Activity Detection | Lightweight neural VAD detecting human speech vs silence for natural barge-in interruption. |
| **Faster-Whisper** | Layer 1 ASR | Speech-to-Text | Quantized CTranslate2 implementation, up to 4x faster than standard Whisper on standard CPUs. |
| **Piper TTS** | Layer 1 TTS | Text-to-Speech | Lightweight neural speech synthesizer running locally with zero cloud API latency or usage fees. |
| **LangGraph** | Layer 2 Orchestrator | Multi-Agent State Machine | Cyclical, stateful agent graph enabling deterministic state transitions and full persistence. |
| **Llama 3 (via Groq / Local)** | Layer 2 Multi-Agent | Clinical symptom extraction | High-speed inference (~300 tokens/sec) paired with offline deterministic NLP fallback. |
| **Regex Safety Gate (F4)** | Layer 2 Safety | Zero-tolerance emergency gate | Sub-millisecond synchronous execution **before** LLM processing to catch life-threatening emergencies. |
| **SHA-256 Hash Chain** | Security & Audit | Tamper-evident audit ledger | Linear cryptographic hash chaining ($H_k = \text{SHA256}(H_{k-1} \parallel \text{data})$) prevents log tampering. |
| **PyJWT & Cryptography** | Layer 4 Security | Role-Based Access Control | Stateless, cryptographically signed tokens separating Doctor, Admin, and Patient views. |
| **Vanilla CSS & Glassmorphism**| Layer 4 Frontend | Modern responsive interface | Zero build steps, instant browser loading, mobile-friendly dark clinical aesthetic. |
| **Pytest & pytest-asyncio** | Quality Assurance | Concurrency & safety tests | Validates multi-agent state, race-condition immunity under high concurrency, and hash integrity. |

---

## ❓ Troubleshooting & FAQ

### 1. What if port 8000 is already in use?
Run Uvicorn on another port, such as 8080:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload
```
Then visit `http://127.0.0.1:8080` in your browser.

### 2. Do I need an expensive GPU to run MAVIS?
**No**. All components (FastAPI, SQLite WAL, in-memory Redis fallback, Piper TTS synthesis, and deterministic triage) run efficiently on any standard modern CPU (Windows, macOS, or Linux).

### 3. Do I need a paid Groq API key?
**No**. While a Groq API key can be added in `.env`, MAVIS includes a built-in deterministic clinical heuristic extractor that runs completely offline with zero API keys required.

### 4. How does MAVIS mathematically prevent double-bookings?
MAVIS enforces a 3-tier defense:
1. **Redis Soft-Hold**: An atomic 180s TTL hold is placed (`SET hold:slot:{id} {call_id} NX EX 180`). Only that caller can proceed.
2. **Database Row Lock**: During booking commit, `SELECT ... FOR UPDATE` locks the slot row.
3. **Composite Unique Constraint**: Schema enforces `UNIQUE(doctor_id, slot_timestamp)` so duplicate bookings are physically rejected at the storage layer.

### 5. How do I reset the database to fresh sample data?
Simply delete the `mavis.db` file (and any `mavis.db-wal` or `mavis.db-shm` files) and restart the server:
```powershell
# Windows PowerShell
Remove-Item mavis.db* -Force
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
The application will automatically re-create the database and re-seed all default doctors, slots, and tokens.

---

## 📤 Pushing Changes to GitHub

To push your project to your GitHub account:

### 1. Initialize Git and Stage Files
```bash
git init
git add .
git commit -m "feat: initial commit of MAVIS - Multi-Agent Voice Intake System"
```

### 2. Create the Repository on GitHub
1. Go to [github.com/new](https://github.com/new).
2. Set Repository Name to: `MAVIS`.
3. Choose **Public** or **Private**.
4. Leave *"Add a README file"*, *"Add .gitignore"*, and *"Choose a license"* **unchecked** (we already created them!).
5. Click **"Create repository"**.

### 3. Link Remote and Push
```bash
git branch -M main
git remote add origin https://github.com/randeepswain/MAVIS.git
git push -u origin main
```

---

## 🎓 Academic Citation & Credits
- **Institution**: M. S. Ramaiah University of Applied Sciences, Bengaluru
- **Department**: Faculty of Engineering and Technology, Dept. of Computer Science and Engineering
- **Project Title**: MAVIS — Multi-Agent Voice Intake System (Batch No. 45)
- **Faculty Guide**: Dr. Sasireka V, Assistant Professor, Dept. of CSE
- **Students**: Sakshi Srivastava, Randeep Swain, Vyshnav Vinod PP, Sridarsh Anand
