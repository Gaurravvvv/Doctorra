from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, oauth
from ..models import Doctor

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.')
            return redirect(url_for('auth.login'))

        if Doctor.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('auth.login'))

        if Doctor.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('auth.login'))

        hashed_pw = generate_password_hash(password)
        new_doctor = Doctor(username=username, email=email, password=hashed_pw)
        db.session.add(new_doctor)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('auth.login'))

    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        doctor = Doctor.query.filter_by(username=username).first()
        
        if doctor and doctor.password and check_password_hash(doctor.password, password):
            session['doctor_id'] = doctor.id
            if not doctor.is_profile_complete:
                 return redirect(url_for('doctor.setup_profile'))
            return redirect(url_for('doctor.dashboard'))
        else:
            flash('Invalid credentials')
            
    return render_template('auth/login.html')

@auth_bp.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
             user_info = oauth.google.get('userinfo').json()

        email = user_info.get('email')
        google_id = user_info.get('sub') 
        
        # 1. Check if Doctor exists with this google_id
        doctor = Doctor.query.filter_by(google_id=google_id).first()

        if doctor:
            session['doctor_id'] = doctor.id
            if not doctor.is_profile_complete:
                 return redirect(url_for('doctor.setup_profile'))
            return redirect(url_for('doctor.dashboard'))

        # 2. If not, check if Doctor exists with this email
        doctor = Doctor.query.filter_by(email=email).first()

        if doctor:
            # Link account
            doctor.google_id = google_id
            db.session.commit()
            session['doctor_id'] = doctor.id
            if not doctor.is_profile_complete:
                 return redirect(url_for('doctor.setup_profile'))
            return redirect(url_for('doctor.dashboard'))
        
        flash('Access Denied: Email not registered. Please Sign Up first.')
        return redirect(url_for('auth.login'))

    except Exception as e:
        print(f"Google Login Error: {e}")
        flash('Authentication failed.')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    session.pop('doctor_id', None)
    return redirect(url_for('auth.login'))
