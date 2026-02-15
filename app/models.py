from datetime import datetime
from sqlalchemy.dialects.mysql import JSON
from .extensions import db

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=True) 
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # New Fields
    full_name = db.Column(db.String(100))
    specialization = db.Column(db.String(100))
    unique_code = db.Column(db.String(50), unique=True, index=True)
    is_profile_complete = db.Column(db.Boolean, default=False)
    
    patients = db.relationship('Patient', backref='doctor', lazy=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=False) 
    
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    visits = db.relationship('Visit', backref='patient', lazy=True)

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    symptoms = db.Column(JSON, nullable=True) 
    status = db.Column(db.String(20), default='filling')  # filling, ready, urgent, treated
    arrival_time = db.Column(db.DateTime, default=datetime.utcnow)
