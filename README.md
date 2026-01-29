# Doctorra 🏥

Doctorra is a Clinic Queue & Intake Management System (MVP) designed to digitize patient intake and streamline clinic operations. It allows patients to perform a "soft login" via a QR code or web link, answer a symptom-based decision tree, and be automatically triaged (Urgent vs. Normal) into a live dashboard for the doctor.

## 🚀 Features

### For Patients
*   **Soft Login:** Quick check-in using Name, Age, and Phone Number.
*   **Symptom Assessment:** Dynamic question flow based on the selected main symptom.
*   **Easy Input:** Multiple-choice questions for common symptoms, with an "Other" option for manual typing.
*   **Real-time Status:** View assigned token number and wait status.

### For Doctors
*   **Live Dashboard:** Auto-refreshing Kanban board (updates every 30 seconds).
*   **Automated Triage:**
    *   🔴 **Urgent:** Red card (e.g., Accident, Breathing Difficulty).
    *   🟢 **Waiting:** Green card (Standard symptoms).
    *   ⚪ **Arriving:** Grey card (Patients currently filling forms).
*   **Patient Details:** Expandable cards to view full symptom history and answers.
*   **Patient History:** A dedicated log of all treated patients, sortable by date/time.

## 🛠️ Tech Stack

*   **Language:** Python 3.x
*   **Framework:** Flask (Micro-framework)
*   **Database:** SQLite (SQLAlchemy ORM)
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript (No heavy frameworks)
*   **Styling:** Custom "Clinical Theme" (CSS Variables)

## ⚙️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd Doctorra
    ```

2.  **Create a Virtual Environment (Optional but Recommended)**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install flask flask-sqlalchemy
    ```

4.  **Run the Application**
    ```bash
    python app.py
    ```
    *   The database (`doctorra.db`) will be automatically created on the first run.
    *   A default admin user is created automatically.

## 📖 Usage Guide

### 1. Patient Interface
*   Open your browser and navigate to `http://127.0.0.1:5000/`.
*   Enter your details to check in.
*   Select your symptoms and answer the specific questions.
*   Receive your token number.

### 2. Doctor Dashboard
*   Navigate to `http://127.0.0.1:5000/login`.
*   **Default Credentials:**
    *   **Username:** `admin`
    *   **Password:** `admin`
*   View the live Kanban board.
*   Click **"View Details"** to see patient answers.
*   Click **"Mark Treated"** to move a patient to the history log.
*   Click **"History"** in the header to view past records.

## 📂 Project Structure

```
Doctorra/
├── app.py                # Main Flask application, models, and routes
├── doctorra.db           # SQLite Database (Created on run)
├── templates/            # HTML Templates
│   ├── base.html         # Base layout with CSS
│   ├── patient_login.html
│   ├── intake.html       # Dynamic symptom form
│   ├── success.html      # Token display
│   ├── login.html        # Doctor login
│   ├── dashboard.html    # Kanban board
│   └── history.html      # Treated patient log
└── README.md             # Project documentation
```

## 📜 License
This project is an MVP created for educational and demonstration purposes.
