import os
import json
import logging
import webbrowser
import threading

from flask import Flask
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from config import Config
from extensions import db, login_manager, mail, socketio, limiter
from flask_migrate import Migrate

logger = logging.getLogger(__name__)

APP_DATA = {}


def load_json_data(app_root_path: str) -> dict:
    json_path = os.path.join(app_root_path, "static", "manifest.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(app_root_path, "static", "data.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(app_root_path, "data.json")

    if not os.path.exists(json_path):
        logger.warning(f"[AppInit] JSON data file not found at {json_path}. Initializing empty data.")
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"[AppInit] Successfully loaded JSON data from {json_path}")
            return data
    except Exception as e:
        logger.error(f"[AppInit] Failed to load JSON data file: {e}")
        return {}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(app.instance_path), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    socketio.init_app(app)

    # Optional rate limiter
    if limiter:
        limiter.init_app(app)
        logger.info("[AppInit] Rate limiting enabled (Flask-Limiter).")
    else:
        logger.warning("[AppInit] Flask-Limiter not installed — rate limiting disabled. "
                       "Install with: pip install flask-limiter")

    migrate = Migrate(app, db)

    global APP_DATA
    with app.app_context():
        APP_DATA = load_json_data(app.root_path)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ------------------------------------------------------------------
    # Blueprint registration
    # ------------------------------------------------------------------
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.lecturer import lecturer_bp
    from routes.admin import admin_bp
    from routes.class_rep import class_rep_bp
    from routes.search import search_bp
    from routes.socket_events import register_socket_events

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(lecturer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(class_rep_bp)
    app.register_blueprint(search_bp)

    register_socket_events(socketio)

    # ------------------------------------------------------------------
    # Jinja filters & context processors
    # ------------------------------------------------------------------
    from app_utils.stats import predict_at_risk_trend

    @app.template_filter('at_risk_trend')
    def at_risk_trend_filter(history, threshold=75):
        _, projected, trending = predict_at_risk_trend(history, threshold)
        return {'projected': projected, 'trending': trending}

    @app.context_processor
    def inject_globals():
        theme = "light"
        if current_user.is_authenticated:
            theme = getattr(current_user, "theme_preference", "light") or "light"
        return {
            "active_theme": theme,
            "app_data": APP_DATA,
            "getattr": getattr,
            "hasattr": hasattr
        }

    @app.context_processor
    def inject_endpoints():
        """
        Injects registered view function names into Jinja context to prevent 
        Jinja BuildErrors when base templates reference routes conditionally.
        """
        return dict(endpoints=set(app.view_functions.keys()))

    @app.context_processor
    def inject_pending_count():
        from models import ClassRep
        count = 0
        if current_user.is_authenticated and getattr(current_user, 'role', '') == 'admin':
            count = ClassRep.query.filter_by(approved=False).count()
        return {'pending_requests_count': count}

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return "Page not found.", 404

    @app.errorhandler(403)
    def forbidden(e):
        return "You do not have permission to access this resource.", 403

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        logger.exception("Unhandled 500 error")
        return "Something went wrong on our end. The team has been notified.", 500

    with app.app_context():
        db.create_all()
        from database.seed import seed_database
        try:
            seed_database()
        except IntegrityError:
            db.session.rollback()

    print(f"🔗 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    return app


app = create_app()


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").strip().lower() in ("1", "true", "yes")
    threading.Timer(1.2, _open_browser).start()
    socketio.run(app, debug=debug_mode, use_reloader=False)