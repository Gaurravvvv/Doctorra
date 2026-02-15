import json
from flask import Flask
from werkzeug.security import generate_password_hash
from config import Config
from .extensions import db, oauth

def get_symptoms_json(symptoms_data):
    if not symptoms_data:
        return {}
    if isinstance(symptoms_data, dict):
        return symptoms_data
    try:
        return json.loads(symptoms_data)
    except:
        return {}

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)
    oauth.init_app(app)
    
    # Register OAuth Consumers
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
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

    # Register Blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.doctor import doctor_bp
    from .blueprints.patient import patient_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)

    # Register Jinja Filters
    app.jinja_env.filters['from_json'] = get_symptoms_json

    # Database Creation & Admin Init
    with app.app_context():
        # Import models to ensure they are known to SQLAlchemy
        from .models import Doctor, Patient, Visit
        db.create_all()
        
        # Create default admin if not exists
        if not Doctor.query.filter_by(username='admin').first():
            hashed_admin_pw = generate_password_hash('admin')
            admin = Doctor(
                username='admin', 
                password=hashed_admin_pw, 
                email='admin@doctorra.com',
                full_name='System Admin',
                specialization='Administration',
                unique_code='DR-ADM-0000',
                is_profile_complete=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created.")

    return app
