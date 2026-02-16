import re
import random
import string
import base64
from io import BytesIO
import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from ..extensions import db
from ..models import Doctor, Patient, Visit

doctor_bp = Blueprint('doctor', __name__)

def generate_doctor_qr(unique_code):
    # Using request.host_url requires request context, which is fine in a route
    # But note: this function is called inside routes.
    # We need to ensure the link points to the PATIENT blueprint route.
    # unique_code is used in /book/<code
    url = request.host_url + 'book/' + unique_code
    # Or cleaner: url_for('patient.book_appointment', unique_code=unique_code, _external=True)
    # Using url_for is safer for blueprints.
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

@doctor_bp.route('/setup-profile', methods=['GET', 'POST'])
def setup_profile():
    if 'doctor_id' not in session:
        return redirect(url_for('auth.login'))
    
    doctor = Doctor.query.get(session['doctor_id'])
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        specialization = request.form.get('specialization')
        
        if not full_name or not specialization:
            flash("All fields are required.")
            return render_template('auth/setup_profile.html')
            
        # Generate Unique ID: DR-XXX-####
        # Taking first 3 letters of name, upper case.
        clean_name = re.sub(r'[^a-zA-Z]', '', full_name).upper()
        prefix = clean_name[:3] if len(clean_name) >= 3 else clean_name.ljust(3, 'X')
        
        # Ensure uniqueness
        while True:
            random_digits = ''.join(random.choices(string.digits, k=4))
            code = f"DR-{prefix}-{random_digits}"
            if not Doctor.query.filter_by(unique_code=code).first():
                break
        
        doctor.full_name = full_name
        doctor.specialization = specialization
        doctor.unique_code = code
        doctor.is_profile_complete = True
        db.session.commit()
        
        return redirect(url_for('doctor.dashboard'))

    return render_template('auth/setup_profile.html')

@doctor_bp.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('auth.login'))
    
    doctor = Doctor.query.get(session['doctor_id'])
    if not doctor.is_profile_complete:
        return redirect(url_for('doctor.setup_profile'))

    # Generate QR Code for this doctor
    # We can use url_for to ensure the link is correct
    # url = url_for('patient.book_appointment', unique_code=doctor.unique_code, _external=True)
    # But helper function does logic. I'll stick to helper for now, but update it inside.
    # Wait, the helper logic `request.host_url + 'book/' + unique_code` assumes root URL structure.
    # The patient blueprint will likely have `url_prefix=''` or `/patient`?
    # User said: `patient.py # Routes: /book, /find-doctor`.
    # I should assume patient blueprint is mounted at root or handles `/book`.
    # Typically user-facing URLs should be clean. 
    # `app.register_blueprint(patient_bp)` (no prefix) -> `/book/<id>` works as before.
    qr_b64 = generate_doctor_qr(doctor.unique_code)

    # Filter visits by doctor's patients
    # Join Visit -> Patient -> Doctor
    visits_urgent = Visit.query.join(Patient).filter(
        Patient.doctor_id == doctor.id, 
        Visit.status == 'urgent'
    ).order_by(Visit.arrival_time).all()
    
    visits_ready = Visit.query.join(Patient).filter(
        Patient.doctor_id == doctor.id, 
        Visit.status == 'ready'
    ).order_by(Visit.arrival_time).all()
    
    visits_filling = Visit.query.join(Patient).filter(
        Patient.doctor_id == doctor.id, 
        Visit.status == 'filling'
    ).order_by(Visit.arrival_time).all()
    
    return render_template('doctor/dashboard.html', 
                           urgent=visits_urgent, 
                           ready=visits_ready, 
                           filling=visits_filling,
                           doctor=doctor,
                           qr_code=qr_b64)

@doctor_bp.route('/mark_treated/<int:visit_id>', methods=['POST'])
def mark_treated(visit_id):
    if 'doctor_id' not in session:
        return redirect(url_for('auth.login'))
        
    visit = Visit.query.get_or_404(visit_id)
    # Ensure this visit belongs to the logged in doctor
    if visit.patient.doctor_id != session['doctor_id']:
        abort(403)
        
    visit.status = 'treated'
    db.session.commit()
    return redirect(url_for('doctor.dashboard'))

@doctor_bp.route('/history')
def history():
    if 'doctor_id' not in session:
        return redirect(url_for('auth.login'))
    
    visits = Visit.query.join(Patient).filter(
        Patient.doctor_id == session['doctor_id'],
        Visit.status == 'treated'
    ).order_by(Visit.arrival_time.desc()).all()
    
    return render_template('doctor/history.html', visits=visits)
