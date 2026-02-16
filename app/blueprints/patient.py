import json
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from sqlalchemy.orm.attributes import flag_modified
from ..extensions import db, llm
from ..models import Doctor, Patient, Visit

patient_bp = Blueprint('patient', __name__)

def get_symptoms_json(symptoms_data):
    if not symptoms_data:
        return {}
    if isinstance(symptoms_data, dict):
        return symptoms_data
    try:
        return json.loads(symptoms_data)
    except:
        return {}

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

@patient_bp.route('/', methods=['GET'])
def index():
    # Redirect root to new patient gateway
    return redirect(url_for('patient.find_doctor'))

@patient_bp.route('/find-doctor', methods=['GET', 'POST'])
def find_doctor():
    if request.method == 'POST':
        unique_code = request.form.get('unique_code')
        if unique_code:
             return redirect(url_for('patient.book_appointment', unique_code=unique_code))
    return render_template('patient/gateway.html')

@patient_bp.route('/book/<unique_code>', methods=['GET', 'POST'])
def book_appointment(unique_code):
    doctor = Doctor.query.filter_by(unique_code=unique_code).first()
    if not doctor:
        abort(404, description="Doctor not found")

    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        phone = request.form.get('phone')
        
        if not name or not age or not phone:
            flash('All fields are required.')
            return redirect(url_for('patient.book_appointment', unique_code=unique_code))

        patient = Patient.query.filter_by(phone=phone).first()
        
        if not patient:
            patient = Patient(name=name, age=int(age), phone=phone, doctor_id=doctor.id)
            db.session.add(patient)
            db.session.commit()
        else:
            patient.name = name
            patient.age = int(age)
            patient.doctor_id = doctor.id
            db.session.commit()

        # Check for existing active visit
        active_visit = Visit.query.filter(
            Visit.patient_id == patient.id,
            Visit.status.in_(['filling', 'ready', 'urgent'])
        ).first()

        if active_visit:
            pass # Silent resume
        else:
            # Create new visit
            active_visit = Visit(patient_id=patient.id, status='filling')
            db.session.add(active_visit)
            db.session.commit()

        # Redirect to the intake flow
        return redirect(url_for('patient.intake', visit_id=active_visit.id))

    return render_template('patient/book.html', doctor=doctor)

@patient_bp.route('/intake/<int:visit_id>', methods=['GET', 'POST'])
def intake(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    
    # Load existing data if any
    current_data = get_symptoms_json(visit.symptoms)

    if request.method == 'POST':
        # PHASE 1: User submits the main category (First Step)
        if 'main_category' in request.form:
            main_category = request.form.get('main_category')
            complaint = request.form.get('complaint_text')

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
            visit.symptoms = current_data
            flag_modified(visit, "symptoms")
            db.session.commit()
            
            return redirect(url_for('patient.intake', visit_id=visit_id))

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
            visit.symptoms = current_data
            
            # Update Status
            is_urgent = current_data.get('urgency') == 'High'
            visit.status = 'urgent' if is_urgent else 'ready'
            
            flag_modified(visit, "symptoms")
            db.session.commit()
            return redirect(url_for('patient.token', visit_id=visit.id))


    return render_template('patient/intake.html', visit=visit, data=current_data)

@patient_bp.route('/token/<int:visit_id>')
def token(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    return render_template('patient/success.html', visit=visit)
