# Doctorra 🏥 - AI-Powered Clinic Queue & Intake Management System

Doctorra is a modern, AI-powered Clinic Queue and Intake Management System designed to digitize patient check-ins, automate triage, and streamline waiting room operations. It replaces manual paperwork with a dynamic, context-aware digital intake form powered by artificial intelligence, visualizing the entire patient flow on a real-time Kanban board for healthcare providers.

---

## 🌟 Key Features & Functional Tour

### 👤 For Patients (Seamless Digital Check-In)
*   **Flexible Access Gateways:**
    *   **Direct QR Scanning:** Patients scan the clinic-specific QR code using their mobile devices to be instantly redirected to the check-in page.
    *   **Manual Doctor ID Entry:** An alternate entry portal allows patients to type in a Doctor's unique clinic code.
    *   **In-App QR Reader:** Uses the integrated `html5-qrcode` library for scanning QR codes using the device camera directly from the gateway page.
*   **Soft Check-In:** Fast entry using only **Name**, **Age**, and **Phone Number**—no complex username/password account creation required.
*   **Visit Resumption:** If an check-in attempt is interrupted, re-entering details with the same phone number triggers a "silent resume" of the active visit rather than duplicating entries.
*   **AI-Driven Triage Questionnaire:**
    *   Powered by **Gemini 2.5 Flash-Lite** via LangChain.
    *   Dynamically generates 6 to 7 context-aware multiple-choice questions based on the patient's primary condition category and detailed description.
    *   **Smart Fallback System:** If the Gemini API is unreachable or key is missing, the application automatically switches to predefined static medical questionnaires, ensuring 100% uptime.
    *   **Interactive Input UI:** Incorporates a dynamic "Other" option for all radio questions, which reveals a hidden text input and dynamically sets it as `required` via client-side JavaScript.
*   **Instant Success Tokens:** Provides patients with an immediate token number (visit ID) and real-time status update once intake is submitted.

### 🩺 For Doctors (Clinic Management Suite)
*   **Secure Authentication:**
    *   **Local Login & Registration:** Password-hashed traditional sign-in.
    *   **Google OAuth2 Integration:** Single sign-on authentication through Google Accounts via `authlib`.
    *   **Automatic Account Linking:** Automatically maps and links Google Accounts to existing doctor profiles if the email matches.
*   **Onboarding & Profile Setup:**
    *   Forces profile setup (Full Name, Specialization) immediately after first login.
    *   Generates a custom clinic ID: `DR-[NamePrefix]-[RandomDigits]` (e.g., `DR-SMI-4819`) and checks database uniqueness.
*   **Live Kanban Dashboard:**
    *   **Auto-Refresh Engine:** Automatically refreshes the dashboard every 30 seconds (`<meta http-equiv="refresh" content="30">`) to update the queue.
    *   **Visually Categorized Columns:**
        *   🔴 **URGENT:** High-priority patients identified by AI triage (chest pain, breathing issues, heavy bleeding, severe trauma).
        *   🟢 **WAITING (READY):** Patients who have completed intake and are ready to be called.
        *   ⚪ **ARRIVING (FILLING):** Patients currently filling out their intake forms, showing their check-in start timestamp.
    *   **Interactive Patient Insights:** Expands inline via a native `<details>` element showing all patient answers instantly without reloading the dashboard.
    *   **AI vs. Standard Badging:** Displays visual tags (`✨ AI` or `📋 Std`) so doctors instantly know if questions were customized by Gemini.
    *   **Actionable Queue Progression:** A single click on "Mark Treated" logs the visit and moves the patient off the queue.
*   **Clinic Asset Management:**
    *   Displays unique clinic ID and pre-generated scan-to-book QR codes.
    *   Features a "Copy Booking Link" button using the HTML5 Clipboard API.
*   **Patient History Archive:**
    *   A searchable log of all treated patients, sorted chronologically (newest first).
    *   Includes full details of their symptoms, timestamps, and triage questionnaire responses.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.10+ / Flask | Modular Blueprint Architecture (`auth`, `doctor`, `patient`) |
| **Database** | MySQL | Stored in Docker volumes, managed via SQLAlchemy ORM |
| **Authentication** | Authlib | Integrates Google OAuth2 and local credentials hashing |
| **AI Engine** | LangChain / Google Gemini 2.5 Flash-Lite | Real-time structured questionnaire generation & triage |
| **Frontend UI** | HTML5, CSS3, Jinja2, Vanilla JS | Responsive, modern grid systems with HSL variables |
| **QR Engine** | Python `qrcode` + `html5-qrcode` (JS) | Generates base64 QR codes (backend) & scans them (frontend) |
| **Containerization** | Docker & Docker Compose | Pre-configured environment setups for services |

---

## 📂 Project Architecture

```
Doctorra/
├── app/
│   ├── blueprints/
│   │   ├── __init__.py  # Blueprint hook-ups
│   │   ├── auth.py      # Registration, Login, Logout, Google OAuth callback
│   │   ├── doctor.py    # Profile setup, Kanban board, history log, QR generator
│   │   └── patient.py   # Clinic search, check-in, AI question intake, tokens
│   ├── static/          # Static assets (CSS, JS, Images)
│   ├── templates/
│   │   ├── auth/
│   │   │   ├── login.html          # Dual login/register slide form
│   │   │   └── setup_profile.html  # Onboarding name & specialization form
│   │   ├── doctor/
│   │   │   ├── dashboard.html      # Kanban board with auto-refresh & inline details
│   │   │   └── history.html        # Treated patient history data-table
│   │   ├── patient/
│   │   │   ├── book.html           # Soft registration intake form
│   │   │   ├── gateway.html        # Camera QR scanner & manual connection
│   │   │   ├── intake.html         # Double-phase symptom descriptions & AI questions
│   │   │   └── success.html        # Digital queue token confirmation card
│   │   └── base.html    # Global styles (custom CSS grid, HSL palette, fonts)
│   ├── __init__.py      # App factory, DB creator, Jinja filters, seed data
│   ├── extensions.py    # Shared instances (db, oauth, langchain ChatGoogleGenerativeAI)
│   └── models.py        # Database entities (Doctor, Patient, Visit)
├── .dockerignore        # Docker exclusion rules
├── .env                 # Environment secrets
├── .gitignore           # Git versioning exclusion rules
├── config.py            # Flask config and load_dotenv
├── docker-compose.yml   # Multi-container service definitions
├── Dockerfile           # Multi-stage Python build container
├── README.md            # Detailed documentation
├── requirements.txt     # Locked Python packages
└── run.py               # WSGI entry point
```

---

## 🧠 Database Schema

```mermaid
erDiagram
    DOCTOR ||--o{ PATIENT : manages
    PATIENT ||--o{ VISIT : undergoes
    
    DOCTOR {
        int id PK
        string username UNIQUE
        string password
        string email UNIQUE
        string google_id UNIQUE
        string full_name
        string specialization
        string unique_code INDEX
        boolean is_profile_complete
    }
    
    PATIENT {
        int id PK
        string name
        int age
        string phone UNIQUE
        int doctor_id FK
    }
    
    VISIT {
        int id PK
        int patient_id FK
        json symptoms "Stores complaint, questions, answers, and triage status"
        string status "filling | ready | urgent | treated"
        datetime arrival_time
    }
```

---

## 🧠 AI Workflow & Prompt Engineering

When a patient submits their initial symptoms, the system coordinates the following workflow:

```mermaid
graph TD
    A[Patient submits Complaint & Category] --> B{Is Gemini API Key configured?}
    B -- Yes --> C[Build LangChain Medical Triage Prompt]
    B -- No --> D[Load Static Fallback Questions for Category]
    C --> E[Invoke ChatGoogleGenerativeAI]
    E --> F[Extract valid JSON via Regex]
    F --> G[Parse Questionnaire & Triage Level]
    D --> H[Store JSON Questionnaire in DB]
    G --> H
    H --> I[Render Dynamic MCQs in Patient UI]
```

### The System Prompt:
```ini
You are a medical triage assistant.
Patient Category: {category}
Patient Complaint: "{patient_complaint_text}"

Return a strictly valid JSON object with the following structure:
{
  "urgency": "High" or "Low", 
  "category": "{category}", 
  "questions": [
     {
       "question_text": "The question string here?",
       "options": ["Option A", "Option B", "Option C", "Option D"]
     }
  ]
}

Instructions:
1. Generate exactly 6 to 7 multiple-choice questions relevant to the complaint.
2. For every question, generate 4 distinct, likely options. Keep options short.
3. Urgency Rules: Set "urgency" to "High" if the complaint involves accidents, trauma, severe pain, breathing difficulties, chest pain, stroke symptoms, or uncontrolled bleeding.
4. Return ONLY valid JSON (no markdown block wrapper).
```

---

## 🐳 Docker Quickstart

The easiest way to run Doctorra is with Docker and Docker Compose.

1.  **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd Doctorra
    ```

2.  **Configure Environment Variables**
    Create a `.env` file in the root directory:
    ```ini
    DATABASE_URL=mysql+mysqlconnector://root:gaurav@db/doctorra
    GEMINI_API_KEY=your_gemini_api_key
    GOOGLE_CLIENT_ID=your_google_client_id
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    SECRET_KEY=your_flask_secret_key
    ```

3.  **Boot Container Services**
    ```bash
    docker-compose up --build
    ```
    This builds the Flask application container and links it to a MySQL 8.0 server container.
    *   The app will be live at `http://localhost:5000`.
    *   The database is exposed locally on port `3307`.

---

## 🚀 Local Development

### Prerequisites
*   Python 3.10+
*   MySQL Server (if not running MySQL via Docker)
*   Google Gemini API Key

### Installation

1.  **Clone & Navigate**
    ```bash
    git clone <repository_url>
    cd Doctorra
    ```

2.  **Environment Setup**
    ```bash
    # Create virtual environment
    python -m venv venv
    
    # Activate virtual environment (Windows)
    venv\Scripts\activate
    
    # Activate virtual environment (macOS/Linux)
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Local Database Configuration**
    Ensure your local MySQL server is running, and adjust the `DATABASE_URL` in `.env` to match your credentials:
    ```ini
    DATABASE_URL=mysql+mysqlconnector://user:password@localhost:3306/doctorra
    GEMINI_API_KEY=your_gemini_api_key
    GOOGLE_CLIENT_ID=your_google_client_id
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    SECRET_KEY=your_flask_secret_key
    ```

5.  **Initialize & Run**
    ```bash
    python run.py
    ```
    *   **Auto-Migration & Database Setup:** On startup, Flask-SQLAlchemy automatically initializes tables and inserts a default admin account:
        *   **Username:** `admin`
        *   **Password:** `admin`
        *   **Clinic ID:** `DR-ADM-0000`

---

## 📜 License
Developed as an MVP for clinical intake optimization, queue visualization, and educational purposes.
