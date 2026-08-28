from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_socketio import SocketIO

# ---------------------------------------------------------------------------
# Core extensions
# ---------------------------------------------------------------------------
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"

# ---------------------------------------------------------------------------
# Optional: Flask-Limiter (install with `pip install flask-limiter`)
# ---------------------------------------------------------------------------
limiter = None
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",  # Upgrade to Redis in production
    )
except ImportError:
    pass