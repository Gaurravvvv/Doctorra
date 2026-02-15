# Doctorra 🏥 - Clinic Queue & Intake Management System

Doctorra is an AI-powered Clinic Queue and Intake Management System designed to digitize patient intake and streamline clinic operations. It transforms the traditional waiting room experience into a dynamic, data-driven workflow.

## 🌟 Key Features

### 👤 For Patients
*   **Soft Login & Check-in:** Simple entry using Name, Age, and Phone Number—no complex accounts needed for immediate care.
*   **AI-Powered Intake:** Uses **Gemini 2.5 Flash-Lite** to generate a context-aware medical questionnaire based on the patient's initial complaint.
*   **Intelligent Triage:** Automatically categorizes patients as "Urgent" or "Normal" based on their AI-generated intake responses.
*   **Real-time Feedback:** Provides patients with a token number and status confirmation immediately after intake completion.

### 🩺 For Doctors
*   **Live Kanban Dashboard:** A real-time board visualizing the patient flow:
    *   🔴 **Urgent:** High-priority cases requiring immediate attention.
    *   🟢 **Ready:** Patients who have completed intake and are waiting.
    *   ⚪ **Arriving:** Patients currently in the process of filling out their intake forms.
*   **Detailed Patient Insights:** Expandable cards showing the full AI-generated questionnaire and patient responses.
*   **Patient History Log:** A searchable and sortable archive of all treated patients for record-keeping.
*   **Secure Authentication:** Supports both traditional username/password and **Google OAuth** for secure access to the medical dashboard.

## 🛠️ Tech Stack

*   **Backend:** Python 3.x, [Flask](https://flask.palletsprojects.com/) (Modular Blueprint Architecture)
*   **Database:** MySQL with [SQLAlchemy ORM](https://www.sqlalchemy.org/)
*   **AI Engine:** [LangChain](https://www.langchain.com/) + [Google Gemini 2.5 Flash-Lite](https://ai.google.dev/) (via `langchain-google-genai`)
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript, Jinja2 Templates
*   **Authentication:** [Authlib](https://docs.authlib.org/) for Google OAuth
*   **Containerization:** Docker & Docker Compose

## 🐳 Docker Quickstart

The easiest way to run Doctorra is with Docker.

1.  **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd Doctorra
    ```

2.  **Configuration**
    Create a `.env` file in the root directory (see [Configuration](#configuration) below for details).

3.  **Run with Compose**
    ```bash
    docker-compose up --build
    ```
    The app will be available at `http://localhost:5000`.

## 🚀 Local Development

### Prerequisites
*   Python 3.8+
*   MySQL Server
*   Google Gemini API Key
*   Google Cloud Console Project (for OAuth)

### Installation

1.  **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd Doctorra
    ```

2.  **Environment Setup**
    ```bash
    # Create and activate virtual environment
    python -m venv venv
    
    # Windows
    venv\Scripts\activate
    
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**
    Create a `.env` file in the root directory:
    ```ini
    DATABASE_URL=mysql+mysqlconnector://user:password@localhost/doctorra
    GEMINI_API_KEY=your_gemini_api_key
    GOOGLE_CLIENT_ID=your_google_client_id
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    SECRET_KEY=your_flask_secret_key
    ```
    *Note: If running locally without Docker, ensure your MySQL server is running and the credentials in `DATABASE_URL` are correct.*

5.  **Initialize & Run**
    ```bash
    python run.py
    ```
    *The application will automatically create the database tables and a default admin user (`admin`/`admin`) on the first run.*

## 📂 Project Architecture

```
Doctorra/
├── app/
│   ├── blueprints/      # Application routes (Auth, Doctor, Patient)
│   ├── static/          # Static assets (CSS, JS, Images)
│   ├── templates/       # Jinja2 HTML templates
│   ├── __init__.py      # App factory & extension initialization
│   ├── extensions.py    # Database & OAuth instances
│   └── models.py        # Database models (User, Patient, Visit)
├── venv/                # Virtual environment
├── .env                 # Environment configuration
├── .dockerignore        # Docker exclusion rules
├── .gitignore           # Git exclusion rules
├── config.py            # Flask configuration class
├── docker-compose.yml   # Docker Compose services
├── Dockerfile           # App container definition
├── README.md            # Project documentation
├── requirements.txt     # Python dependencies
└── run.py               # Application entry point
```

## 🧠 AI Workflow

1.  **Complaint Submission:** Patient provides a brief description (e.g., "Sharp chest pain").
2.  **Prompt Engineering:** The app sends the complaint and category to Gemini via LangChain with a structured medical triage prompt.
3.  **Dynamic JSON Generation:** Gemini returns a JSON object containing tailored questions, options, and an initial urgency assessment.
4.  **Intake Execution:** The UI dynamically renders these questions for the patient.
5.  **Status Update:** Upon completion, the visit is flagged as `urgent` or `ready` on the doctor's board.

## 📜 License
Developed as an MVP for clinical intake optimization and educational purposes.
