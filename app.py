import os
import json
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.security import generate_password_hash, check_password_hash
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'doctorra-secret-key-123'
# MySQL Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+mysqlconnector://root:password@localhost/doctorra')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 280}

# Configure Gemini API via LangChain
llm = None
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GENAI_API_KEY:
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.2,
            max_output_tokens=2000,
            google_api_key=GENAI_API_KEY
        )
        print("INFO: Gemini API Key loaded. LLM initialized.")
    except Exception as e:
        print(f"ERROR: Failed to initialize LLM: {e}")
else:
    print("WARNING: GEMINI_API_KEY not found in environment. AI features will be disabled.")

db = SQLAlchemy(app)

# --- OAuth Configuration ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'claims_options': {
            'iss': {
                'values': ['https://accounts.google.com', 'accounts.google.com']
            }
        }
    }
)

# --- Data Models ---

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    visits = db.relationship('Visit', backref='patient', lazy=True)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    # Increased length for hash
    password = db.Column(db.String(255), nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=True) 
    google_id = db.Column(db.String(100), unique=True, nullable=True) 

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    symptoms = db.Column(JSON, nullable=True) 
    status = db.Column(db.String(20), default='filling')  # filling, ready, urgent, treated
    arrival_time = db.Column(db.DateTime, default=datetime.utcnow)

# --- Logic & Rules ---

def get_ai_triage(category, patient_complaint_text):
    # --- Fallback Data (Offline Mode) ---
    FALLBACK_QUESTIONS = {
        "Accident/Trauma": {
            "urgency": "High",
            "category": "Accident/Trauma",
            "questions": [
                {"question_text": "Is there active bleeding?", "options": ["Yes, heavy bleeding", "Yes, minor bleeding", "No", "Not sure"]},
                {"question_text": "Did you lose consciousness?", "options": ["Yes", "No", "Briefly", "Not sure"]},
                {"question_text": "Can you move the injured part?", "options": ["Yes, fully", "Yes, but painful", "No, impossible", "N/A"]},
                {"question_text": "Is there visible swelling or deformity?", "options": ["Severe swelling/deformity", "Mild swelling", "No visible change", "Not sure"]},
                {"question_text": "Rate your pain (1-10)", "options": ["1-3 (Mild)", "4-6 (Moderate)", "7-9 (Severe)", "10 (Unbearable)"]},
                {"question_text": "When did this happen?", "options": ["Just now", "Within 1 hour", "Today", "Yesterday or earlier"]}
            ]
        },
        "Fever/Flu": {
            "urgency": "Low",
            "category": "Fever/Flu",
            "questions": [
                {"question_text": "What is your current temperature?", "options": ["98-99°F", "100-101°F", "102-103°F", "Above 103°F"]},
                {"question_text": "How long have you had the fever?", "options": ["Since today", "1-2 days", "3-5 days", "More than 5 days"]},
                {"question_text": "Do you have difficulty breathing?", "options": ["Yes", "No", "Only when active", "Not sure"]},
                {"question_text": "Do you have a severe headache/stiff neck?", "options": ["Yes", "No", "Mild headache", "Not sure"]},
                {"question_text": "Any other symptoms?", "options": ["Cough/Cold", "Body aches", "Vomiting", "None"]},
                {"question_text": "Have you taken any medication?", "options": ["Yes", "No", "Not yet", "Can't remember"]}
            ]
        },
        "Stomach/Digestion": {
            "urgency": "Low",
            "category": "Stomach/Digestion",
            "questions": [
                {"question_text": "Where is the pain located?", "options": ["Upper abdomen", "Lower abdomen", "All over", "No pain"]},
                {"question_text": "Do you have vomiting or nausea?", "options": ["Yes, vomiting", "Yes, nausea only", "No", "Occasionally"]},
                {"question_text": "Do you have loose motions (diarrhea)?", "options": ["Yes, frequently", "Yes, mild", "No", "Constipated instead"]},
                {"question_text": "Is there blood in stool/vomit?", "options": ["Yes", "No", "Not sure", "Black stool"]},
                {"question_text": "How severe is the pain?", "options": ["Mild", "Moderate", "Severe", "Unbearable"]},
                {"question_text": "Last meal time?", "options": ["Within 2 hours", "Today morning", "Yesterday", "Fasting"]}
            ]
        },
        "Breathing Issue": {
            "urgency": "High",
            "category": "Breathing Issue",
            "questions": [
                {"question_text": "Do you have chest pain?", "options": ["Yes, crushing pain", "Yes, mild pain", "No", "Tightness only"]},
                {"question_text": "Is it hard to speak full sentences?", "options": ["Yes", "No", "Slightly", "Not sure"]},
                {"question_text": "Do you have a history of asthma/heart disease?", "options": ["Yes, Asthma", "Yes, Heart Disease", "Both", "None"]},
                {"question_text": "Are your lips or face turning blue?", "options": ["Yes", "No", "Pale", "Not sure"]},
                {"question_text": "Are you wheezing?", "options": ["Yes", "No", "Not sure", "Only when lying down"]},
                {"question_text": "Rate your difficulty (1-10)", "options": ["1-3 (Mild)", "4-6 (Moderate)", "7-9 (Severe)", "10 (Emergency)"]}
            ]
        },
        "General Discomfort": {
            "urgency": "Low",
            "category": "General",
            "questions": [
                {"question_text": "What is the main issue?", "options": ["Pain", "Weakness", "Dizziness", "Other"]},
                {"question_text": "How long has this been happening?", "options": ["Just started", "Few hours", "Days", "Weeks"]},
                {"question_text": "Rate the severity", "options": ["Mild", "Moderate", "Severe", "Unbearable"]},
                {"question_text": "Do you have any known medical conditions?", "options": ["Diabetes", "Hypertension", "Both", "None"]},
                {"question_text": "Are you on medication?", "options": ["Yes", "No", "Sometimes", "Not sure"]},
                {"question_text": "Can you walk/move normally?", "options": ["Yes", "No", "With difficulty", "Not sure"]}
            ]
        }
    }

    if not llm:
        print("DEBUG: LLM object is None. Falling back to offline questions.")
        res = FALLBACK_QUESTIONS.get(category, FALLBACK_QUESTIONS["General Discomfort"]).copy()
        res['is_ai'] = False
        return res
    
    prompt = f"""
    You are a medical triage assistant.
    Patient Category: {category}
    Patient Complaint: "{patient_complaint_text}"
    
    Return a strictly valid JSON object with the following structure:
    {{
      "urgency": "High" or "Low", 
      "category": "{category}", 
      "questions": [
         {{
           "question_text": "The question string here?",
           "options": ["Option A", "Option B", "Option C", "Option D"]
         }}
      ]
    }}
    
    Instructions:
    1. Generate exactly 6 to 7 multiple-choice questions relevant to the complaint to help a doctor assess the situation.
    2. For every question, generate 4 distinct, likely options. Keep options short.
    3. Urgency Rules: Set "urgency" to "High" if the complaint involves accidents, trauma, severe pain, breathing difficulties, chest pain, stroke symptoms, or uncontrolled bleeding. Otherwise set to "Low".
    4. Do NOT include markdown formatting (like ```json). Just the raw JSON string.
    5. Ensure the JSON is valid and parseable.
    """
    
    print(f"DEBUG: Invoking AI for category '{category}'...")
    try:
        response_content = llm.invoke(prompt).content
        text = response_content.strip()
        print(f"DEBUG: AI Raw Response: {text[:200]}...") # Log first 200 chars

        # Improved JSON Extraction
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
            data = json.loads(text)
            data['is_ai'] = True
            print("DEBUG: AI JSON parsed successfully.")
            return data
        else:
            raise ValueError("No JSON object found in AI response")

    except Exception as e:
        print(f"ERROR: AI Generation Failed: {e}")
        print(f"DEBUG: Switching to fallback for {category}.")
        res = FALLBACK_QUESTIONS.get(category, FALLBACK_QUESTIONS["General Discomfort"]).copy()
        res['is_ai'] = False
        return res


# --- Helpers ---

def get_symptoms_json(symptoms_data):
    if not symptoms_data:
        return {}
    if isinstance(symptoms_data, dict):
        return symptoms_data
    try:
        return json.loads(symptoms_data)
    except:
        return {}

app.jinja_env.filters['from_json'] = get_symptoms_json

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        phone = request.form.get('phone')

        if not name or not age or not phone:
            flash('All fields are required.')
            return redirect(url_for('patient_login'))

        # Check if patient exists, else create
        patient = Patient.query.filter_by(phone=phone).first()
        if not patient:
            patient = Patient(name=name, age=int(age), phone=phone)
            db.session.add(patient)
            db.session.commit()
        else:
            # Update info if changed
            patient.name = name
            patient.age = int(age)
            db.session.commit()

        # Check for existing active visit
        active_visit = Visit.query.filter(
            Visit.patient_id == patient.id,
            Visit.status.in_(['filling', 'ready', 'urgent'])
        ).first()

        if active_visit:
            flash('Resuming your active session.')
            if active_visit.status == 'filling':
                return redirect(url_for('intake', visit_id=active_visit.id))
            else:
                return redirect(url_for('token', visit_id=active_visit.id))

        # Create new visit
        visit = Visit(patient_id=patient.id, status='filling')
        db.session.add(visit)
        db.session.commit()

        return redirect(url_for('intake', visit_id=visit.id))

    return render_template('patient_login.html')

@app.route('/intake/<int:visit_id>', methods=['GET', 'POST'])
def intake(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    
    # Load existing data if any
    current_data = get_symptoms_json(visit.symptoms)

    if request.method == 'POST':
        # PHASE 1: User submits the main category (First Step)
        if 'main_category' in request.form:
            main_category = request.form.get('main_category')
            complaint = request.form.get('complaint_text')

            # Optional description handling
            if not complaint or complaint.strip() == "":
                complaint = "None provided"
            
            # Call AI
            ai_result = get_ai_triage(main_category, complaint)
            
            # Save generated questions to DB
            current_data = {
                "Complaint": complaint,
                "Main Symptom": main_category,
                "urgency": ai_result.get('urgency', 'Low'),
                "category": ai_result.get('category', 'General'),
                "questions": ai_result.get('questions', []),
                "is_ai": ai_result.get('is_ai', False)
            }
            # MySQL JSON column accepts dict directly
            visit.symptoms = current_data
            flag_modified(visit, "symptoms")
            db.session.commit()
            
            # Re-render to show questions (GET block will handle display based on data presence)
            return redirect(url_for('intake', visit_id=visit_id))

        # PHASE 2: User submits answers
        if 'submit_answers' in request.form:
            questions = current_data.get('questions', [])
            answers = {}
            
            for i, q in enumerate(questions):
                q_text = q['question_text']
                val = request.form.get(f"answer_{i}")
                if val == "Other":
                    other_val = request.form.get(f"other_{i}")
                    val = other_val if other_val else "Other (Not specified)"
                
                answers[q_text] = val if val else "Skipped"

            current_data['Answers'] = answers
            # MySQL JSON column accepts dict directly
            visit.symptoms = current_data
            
            # Update Status
            is_urgent = current_data.get('urgency') == 'High'
            visit.status = 'urgent' if is_urgent else 'ready'
            
            flag_modified(visit, "symptoms")
            db.session.commit()
            return redirect(url_for('token', visit_id=visit.id))


    return render_template('intake.html', visit=visit, data=current_data)

@app.route('/token/<int:visit_id>')
def token(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    return render_template('success.html', visit=visit)

# --- Doctor Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    # POST is handled within the login page if we use a single page, 
    # but separate route logic is cleaner.
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.')
            return redirect(url_for('doctor_login'))

        # Check existing email
        if Doctor.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('doctor_login'))

        # Create new doctor
        hashed_pw = generate_password_hash(password)
        new_doctor = Doctor(username=username, email=email, password=hashed_pw)
        db.session.add(new_doctor)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('doctor_login'))

    return redirect(url_for('doctor_login'))

@app.route('/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        # Distinguish Login vs Register based on form fields or action?
        # Typically separate forms post to separate routes, or same route with different hidden fields.
        # Here we'll stick to standard login logic for this route.
        username = request.form.get('username')
        password = request.form.get('password')
        
        doctor = Doctor.query.filter_by(username=username).first()
        
        # Verify password hash
        if doctor and doctor.password and check_password_hash(doctor.password, password):
            session['doctor_id'] = doctor.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
            
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
             user_info = google.get('userinfo').json()

        email = user_info.get('email')
        google_id = user_info.get('sub') 
        name = user_info.get('name', email.split('@')[0]) 

        # 1. Check if Doctor exists with this google_id
        doctor = Doctor.query.filter_by(google_id=google_id).first()

        if doctor:
            session['doctor_id'] = doctor.id
            return redirect(url_for('dashboard'))

        # 2. If not, check if Doctor exists with this email
        doctor = Doctor.query.filter_by(email=email).first()

        if doctor:
            # Link account
            doctor.google_id = google_id
            db.session.commit()
            session['doctor_id'] = doctor.id
            return redirect(url_for('dashboard'))
        
        # 3. IF NO MATCH: Forbidden (Or auto-register?)
        # PRD said "Access Denied" previously, keeping it consistent.
        # But for UX, maybe auto-register is better? Sticking to strict requirement for now.
        flash('Access Denied: Email not registered. Please Sign Up first.')
        return redirect(url_for('doctor_login'))

    except Exception as e:
        print(f"Google Login Error: {e}")
        flash('Authentication failed.')
        return redirect(url_for('doctor_login'))

@app.route('/logout')
def logout():
    session.pop('doctor_id', None)
    return redirect(url_for('doctor_login'))

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))
    
    visits_urgent = Visit.query.filter_by(status='urgent').order_by(Visit.arrival_time).all()
    visits_ready = Visit.query.filter_by(status='ready').order_by(Visit.arrival_time).all()
    visits_filling = Visit.query.filter_by(status='filling').order_by(Visit.arrival_time).all()
    
    return render_template('dashboard.html', 
                           urgent=visits_urgent, 
                           ready=visits_ready, 
                           filling=visits_filling)

@app.route('/mark_treated/<int:visit_id>', methods=['POST'])
def mark_treated(visit_id):
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))
        
    visit = Visit.query.get_or_404(visit_id)
    visit.status = 'treated'
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/history')
def history():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))
    
    visits = Visit.query.filter_by(status='treated').order_by(Visit.arrival_time.desc()).all()
    
    return render_template('history.html', visits=visits)

# --- Initialization ---

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not Doctor.query.filter_by(username='admin').first():
            hashed_admin_pw = generate_password_hash('admin')
            admin = Doctor(username='admin', password=hashed_admin_pw, email='admin@doctorra.com')
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
