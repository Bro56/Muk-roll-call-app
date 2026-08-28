import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

class Config:
    # ------------------- SECRET KEY -------------------
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # ------------------- DATABASE -------------------
    # Get environment: 'development' or 'production'
    ENV = os.environ.get('FLASK_ENV', 'development')
    
    # PostgreSQL for production, SQLite for development
    if ENV == 'production':
        # Production: PostgreSQL
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'postgresql://rollcall_user:your_password@localhost:5432/rollcall_db'
    else:
        # Development: SQLite (fast and easy for testing)
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pooling for PostgreSQL (improves performance)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 20)),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 300)),
        'pool_pre_ping': True,
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 50)),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
    }

    # ------------------- UPLOAD FOLDER -------------------
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'face_photos')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit for face uploads

    # ------------------- MAIL (for password reset) -------------------
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.mailtrap.io'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 2525)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'your-mailtrap-username'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'your-mailtrap-password'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@rollcall.mak.ac.ug'
    
    # ------------------- ATTENDANCE -------------------
    ATTENDANCE_THRESHOLD = 75  # Percentage required to be considered "at risk"

    FACE_MATCH_TOLERANCE = float(os.environ.get('FACE_MATCH_TOLERANCE') or 0.5)
    SESSION_CODE_VALID_MINUTES = int(os.environ.get('SESSION_CODE_VALID_MINUTES') or 15)

    # ------------------- GPS CHECK-IN -------------------
    GPS_BASE_RADIUS_METRES = float(os.environ.get('GPS_BASE_RADIUS_METRES') or 40)
    GPS_MAX_ACCURACY_BUFFER_METRES = float(os.environ.get('GPS_MAX_ACCURACY_BUFFER_METRES') or 25)
    GPS_REP_ACCURACY_WARN_METRES = float(os.environ.get('GPS_REP_ACCURACY_WARN_METRES') or 35)

    # ------------------- FALLBACK / RECTIFY -------------------
    RECTIFY_ATTEMPTS_BEFORE_QUEUE = int(os.environ.get('RECTIFY_ATTEMPTS_BEFORE_QUEUE') or 2)
    RECTIFY_TOKEN_TTL_SECONDS = int(os.environ.get('RECTIFY_TOKEN_TTL_SECONDS') or 60)
    RECTIFY_QUEUE_GRACE_MINUTES = int(os.environ.get('RECTIFY_QUEUE_GRACE_MINUTES') or 15)

    # ------------------- CLASS REPS -------------------
    MAX_CLASS_REPS_PER_PROGRAMME = int(os.environ.get('MAX_CLASS_REPS_PER_PROGRAMME') or 4)

    # ------------------- OTHER -------------------
    DEFAULT_THEME = 'light'

    # ------------------- PRODUCTION SAFETY -------------------
    if not os.environ.get('SECRET_KEY') and os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(
            "SECRET_KEY environment variable must be set in production. "
            "Refusing to start with the default development key."
        )