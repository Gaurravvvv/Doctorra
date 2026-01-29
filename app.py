import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'doctorra-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///doctorra.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
    password = db.Column(db.String(100), nullable=False)

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    symptoms = db.Column(db.Text, nullable=True)  # Stored as JSON string
    status = db.Column(db.String(20), default='filling')  # filling, ready, urgent, treated
    arrival_time = db.Column(db.DateTime, default=datetime.utcnow)

# --- Logic & Rules ---

SYMPTOMS = {
    "Fever": {
        "urgent": False,
        "questions": [
            {"text": "How many days have you had fever?", "options": ["1 day", "2 days", "3-5 days", "More than 5 days"]},
            {"text": "Do you have chills?", "options": ["Yes", "No"]},
            {"text": "Current temperature (if known)?", "options": []}  # Empty options means text input
        ]
    },
    "Stomach Issue": {
        "urgent": False,
        "questions": [
            {"text": "Is it Pain, Vomiting, or Loose Motion?", "options": ["Pain", "Vomiting", "Loose Motion", "All of the above"]},
            {"text": "How long has it persisted?", "options": ["Since today", "Since yesterday", "Couple of days", "A week or more"]}
        ]
    },
    "Accident/Injury": {
        "urgent": True,
        "questions": [
            {"text": "Is there active bleeding?", "options": ["Yes", "No"]},
            {"text": "Which body part is injured?", "options": ["Head", "Arm/Hand", "Leg/Foot", "Chest/Back"]},
            {"text": "When did it happen?", "options": ["Just now", "Within the last hour", "Earlier today", "Yesterday"]}
        ]
    },
    "Breathing Difficulty": {
        "urgent": True,
        "questions": [
            {"text": "Do you have chest pain?", "options": ["Yes", "No"]},
            {"text": "History of asthma?", "options": ["Yes", "No"]}
        ]
    },
    "Other": {
        "urgent": False,
        "questions": [
            {"text": "Please describe your symptoms briefly.", "options": []}
        ]
    }
}

# --- Helpers ---

def get_symptoms_json(symptoms_data):
    if not symptoms_data:
        return {}
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

        # Create new visit
        visit = Visit(patient_id=patient.id, status='filling')
        db.session.add(visit)
        db.session.commit()

        return redirect(url_for('intake', visit_id=visit.id))

    return render_template('patient_login.html')

@app.route('/intake/<int:visit_id>', methods=['GET', 'POST'])
def intake(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    
    if request.method == 'POST':
        selected_symptom = request.form.get('main_symptom')
        
        # Check if this is the final submission
        if 'answers' in request.form:
             symptom_key = request.form.get('selected_symptom_key')
             if not symptom_key or symptom_key not in SYMPTOMS:
                 flash("Invalid symptom selected")
                 return redirect(url_for('intake', visit_id=visit_id))
             
             symptom_def = SYMPTOMS[symptom_key]
             answers = {}
             for q_obj in symptom_def['questions']:
                 q_text = q_obj['text']
                 # We try to get the radio selection first
                 val = request.form.get(q_text)
                 # If the value is "Other", we look for the specific other input
                 if val == "Other":
                     other_val = request.form.get(q_text + "_other")
                     val = other_val if other_val else "Other (Not specified)"
                 
                 answers[q_text] = val if val else ""
             
             final_data = {
                 "Main Symptom": symptom_key,
                 "Answers": answers
             }
             
             visit.symptoms = json.dumps(final_data)
             
             # Status Logic
             if symptom_def['urgent']:
                 visit.status = 'urgent'
             else:
                 visit.status = 'ready'
                 
             db.session.commit()
             return redirect(url_for('token', visit_id=visit.id))

    return render_template('intake.html', visit=visit, symptoms=SYMPTOMS)

@app.route('/token/<int:visit_id>')
def token(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    return render_template('success.html', visit=visit)

# --- Doctor Routes ---

@app.route('/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        doctor = Doctor.query.filter_by(username=username).first()
        if doctor and doctor.password == password:
            session['doctor_id'] = doctor.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('doctor_id', None)
    return redirect(url_for('doctor_login'))

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('doctor_login'))
    
    # Filter visits
    # Exclude treated from the board? PRD says "removes from board" for treated.
    # So we fetch status filling, ready, urgent.
    
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
    
    # Fetch treated visits, newest first
    visits = Visit.query.filter_by(status='treated').order_by(Visit.arrival_time.desc()).all()
    
    return render_template('history.html', visits=visits)

# --- Initialization ---

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not Doctor.query.filter_by(username='admin').first():
            admin = Doctor(username='admin', password='admin')
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
