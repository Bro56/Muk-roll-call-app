from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import hashlib
import logging
import os
import json

# ✅ FIXED: WebAuthn imports with try/except fallback
try:
    from webauthn import generate_registration_options, verify_registration_response
    from webauthn import generate_authentication_options, verify_authentication_response
    from webauthn.helpers.structs import AuthenticationExtensionsLargeBlobInputs, AuthenticationExtensionsLargeBlobOutputs
    from webauthn.helpers import base64url_to_bytes, options_to_json
    WEBAUTHN_AVAILABLE = True
except (ImportError, AttributeError) as e:
    WEBAUTHN_AVAILABLE = False
    # Placeholder functions to prevent errors
    def generate_registration_options(*args, **kwargs): return {}
    def verify_registration_response(*args, **kwargs): return {}
    def generate_authentication_options(*args, **kwargs): return {}
    def verify_authentication_response(*args, **kwargs): return {}
    AuthenticationExtensionsLargeBlobInputs = None
    AuthenticationExtensionsLargeBlobOutputs = None
    def base64url_to_bytes(*args, **kwargs): return b''
    def options_to_json(*args, **kwargs): return '{}'

from extensions import db, mail
from models import (
    User, StudentProfile, Programme, College, ClassRep,
    PasswordResetToken, EmailVerificationToken, LecturerActivationCode,
    WebAuthnCredential  # ✅ Make sure this exists in models
)
from app_utils.face_utils import decode_base64_image, extract_face_encoding, save_reference_photo, FaceError
from app_utils.notifications import notify_admins

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)

RP_ID = os.environ.get('RP_ID', 'localhost')
RP_NAME = "Makerere Roll Call"


# --- Token helpers ---
def generate_timed_token(email, salt):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=salt)

def verify_timed_token(token, salt, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=salt, max_age=expiration)
    except Exception:
        return None
    return email


# --- Email verification ---
def generate_verification_token(email):
    return generate_timed_token(email, 'email-verify-salt')

def verify_verification_token(token):
    return verify_timed_token(token, 'email-verify-salt', expiration=86400)

def send_verification_email(user, token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    EmailVerificationToken.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    vt = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(vt)
    db.session.commit()

    verify_url = url_for('auth.verify_email', token=token, _external=True)
    msg = Message('Verify your Roll Call account', recipients=[user.email])
    msg.body = f'''Hi {user.full_name},

Welcome to Makerere Roll Call! Please verify your email by clicking the link below:

{verify_url}

This link expires in 24 hours.

If you did not create this account, please ignore this email.
'''
    try:
        mail.send(msg)
    except Exception:
        logger.exception("Failed to send verification email to %s", user.email)


# --- Password reset ---
def generate_reset_token(email):
    return generate_timed_token(email, 'password-reset-salt')

def verify_reset_token(token, expiration=3600):
    return verify_timed_token(token, 'password-reset-salt', expiration)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for(f"{current_user.role}.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(f"{current_user.role}.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "student")

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Incorrect username or password.", "error")
            return render_template("login.html", role=selected_role, username=username)

        if user.role != 'admin' and not user.email_verified:
            flash("Please verify your email before logging in. Check your inbox or request a new link below.", "error")
            return redirect(url_for('auth.resend_verification', email=user.email))

        if user.role == "admin":
            login_user(user)
            flash(f"Welcome back, {user.full_name} (Admin).", "success")
            return redirect(url_for("admin.dashboard"))

        if selected_role == "classrep":
            classrep = ClassRep.query.filter_by(user_id=user.id, approved=True).first()
            if classrep:
                login_user(user)
                flash(f"Welcome back, {user.full_name} (Class Rep).", "success")
                return redirect(url_for("class_rep.dashboard"))
            else:
                flash("You are not an approved class representative.", "error")
                return render_template("login.html", role=selected_role, username=username)

        if selected_role == "student":
            if user.role == "student":
                login_user(user)
                flash(f"Welcome back, {user.full_name}.", "success")
                return redirect(url_for("student.dashboard"))
            else:
                flash(f"That account is registered as '{user.role}', not 'student'.", "error")
                return render_template("login.html", role=selected_role, username=username)

        if selected_role == "lecturer":
            if user.role == "lecturer":
                login_user(user)
                flash(f"Welcome back, {user.full_name}.", "success")
                return redirect(url_for("lecturer.dashboard"))
            else:
                flash(f"That account is registered as '{user.role}', not 'lecturer'.", "error")
                return render_template("login.html", role=selected_role, username=username)

        flash("Invalid role selection. Please try again.", "error")
        return render_template("login.html", role="student", username=username)

    return render_template("login.html", role=request.args.get("role", "student"))


@auth_bp.route("/signup/student", methods=["GET", "POST"])
def signup_student():
    programmes = Programme.query.order_by(Programme.name).all()
    colleges = College.query.order_by(College.name).all()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip()
        student_number = request.form.get("student_number", "").strip()
        registration_number = request.form.get("registration_number", "").strip()
        programme_id = request.form.get("programme_id")
        year_of_study = request.form.get("year_of_study", 1)
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        face_image_data = request.form.get("face_image_data", "")

        errors = []
        if not full_name or not username or not password:
            errors.append("Please fill in all required fields.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")
        if not programme_id:
            errors.append("Please select your programme.")
        if not face_image_data:
            errors.append("Please capture your face photo for biometric roll call to work.")
        if not email:
            errors.append("Email address is required.")
        elif User.query.filter_by(email=email).first():
            errors.append("That email is already registered.")
        if not registration_number:
            errors.append("Registration number is required.")
        elif StudentProfile.query.filter_by(registration_number=registration_number).first():
            errors.append("That registration number is already taken.")

        face_encoding = None
        face_photo_filename = None
        if face_image_data and not errors:
            try:
                rgb_array, pil_image = decode_base64_image(face_image_data)
                face_encoding, _ = extract_face_encoding(rgb_array)
                face_photo_filename = save_reference_photo(
                    pil_image, current_app.config["UPLOAD_FOLDER"], username
                )
            except FaceError as e:
                errors.append(str(e))

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("signup_student.html", programmes=programmes, colleges=colleges, form=request.form)

        user = User(full_name=full_name, username=username, email=email, role="student", email_verified=False)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        profile = StudentProfile(
            user_id=user.id,
            student_number=student_number or None,
            registration_number=registration_number or None,
            programme_id=int(programme_id),
            year_of_study=int(year_of_study),
            face_encoding=face_encoding,
            face_photo_path=face_photo_filename,
        )
        import datetime
        profile.face_enrolled_at = datetime.datetime.utcnow()
        db.session.add(profile)
        db.session.commit()

        token = generate_verification_token(email)
        send_verification_email(user, token)

        flash("Account created! Please check your email to verify your account before logging in.", "success")
        return redirect(url_for("auth.check_email"))

    return render_template("signup_student.html", programmes=programmes, colleges=colleges, form={})


# ============================================================================
# LECTURER SIGNUP — TWO-STEP GATED FLOW (Code First, Details Second)
# ============================================================================

@auth_bp.route("/signup/lecturer", methods=["GET", "POST"])
def signup_lecturer():
    """
    Step 1: Student sees ONLY an activation code field.
    No name, no email, no password — nothing to scrape or spam.
    """
    if request.method == "POST":
        raw = request.form.get("activation_code", "").strip().upper().replace(" ", "").replace("-", "")
        if len(raw) != 12:
            flash("Invalid code format. Please enter the 12-character code provided by your administrator.", "error")
            return render_template("lecturer_verify_code.html")

        # Normalize to XXXX-XXXX-XXXX
        code = '-'.join([raw[i:i+4] for i in range(0, 12, 4)])

        activation = LecturerActivationCode.query.filter_by(code=code).first()
        if not activation:
            flash("Invalid activation code. Please contact your department administrator.", "error")
            return render_template("lecturer_verify_code.html")

        if activation.used_at:
            flash("This activation code has already been redeemed. Each code can only be used once.", "error")
            return render_template("lecturer_verify_code.html")

        if activation.is_expired:
            flash("This activation code has expired (codes are valid for one semester). Please request a new one from your administrator.", "error")
            return render_template("lecturer_verify_code.html")

        # CRITICAL FIX: Check if admin has revoked this code
        if not activation.is_active:
            flash("This activation code has been revoked by the administrator. Please request a new code.", "error")
            return render_template("lecturer_verify_code.html")

        # Gate passed — stamp the session and redirect to details
        session["lecturer_activation_code_id"] = activation.id
        return redirect(url_for("auth.signup_lecturer_details"))

    return render_template("lecturer_verify_code.html")


@auth_bp.route("/signup/lecturer/details", methods=["GET", "POST"])
def signup_lecturer_details():
    """
    Step 2: Collect profile details ONLY after code is validated.
    The code is verified again on POST to prevent race-condition double-spend.
    """
    activation_id = session.get("lecturer_activation_code_id")
    if not activation_id:
        flash("Please enter your activation code first.", "error")
        return redirect(url_for("auth.signup_lecturer"))

    activation = LecturerActivationCode.query.get(activation_id)
    if not activation or activation.used_at or activation.is_expired or not activation.is_active:
        session.pop("lecturer_activation_code_id", None)
        flash("Your activation code is no longer valid. Please start again.", "error")
        return redirect(url_for("auth.signup_lecturer"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        errors = []
        if not full_name or not username or not password:
            errors.append("Please fill in all required fields.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")
        if not email:
            errors.append("Email address is required.")
        elif User.query.filter_by(email=email).first():
            errors.append("That email is already registered.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("signup_lecturer.html", form=request.form, activation=activation)

        # Race-condition guard: re-check code hasn't been consumed in the milliseconds since Step 1
        activation = LecturerActivationCode.query.filter_by(
            id=activation_id, used_at=None, is_active=True
        ).first()
        if not activation:
            flash("This activation code was just used by someone else or has been revoked. Please request a new code.", "error")
            return redirect(url_for("auth.signup_lecturer"))

        user = User(
            full_name=full_name,
            username=username,
            email=email,
            role="lecturer",
            email_verified=False
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        activation.used_at = datetime.utcnow()
        activation.used_by = user.id
        db.session.commit()

        # Immediate admin alert — dedup disabled (dedup_hours=0) because this is critical
        notify_admins(
            message=f"New lecturer account created: {user.full_name} ({user.email}). "
                    f"Activation code {activation.code} was redeemed.",
            link=url_for("admin.users"),
            dedup_hours=0
        )

        token = generate_verification_token(email)
        send_verification_email(user, token)

        session.pop("lecturer_activation_code_id", None)
        flash("Account created! Please check your email to verify your account before logging in.", "success")
        return redirect(url_for("auth.check_email"))

    return render_template("signup_lecturer.html", form={}, activation=activation)


# ============================================================================
# END LECTURER SIGNUP CHANGES
# ============================================================================


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/toggle-theme", methods=["POST"])
@login_required
def toggle_theme():
    current_user.theme_preference = "dark" if current_user.theme_preference == "light" else "light"
    db.session.commit()
    return jsonify({"theme": current_user.theme_preference})


# --- Cascading dropdowns ---
@auth_bp.route("/api/schools/<int:college_id>")
def api_schools(college_id):
    from models import School
    schools = School.query.filter_by(college_id=college_id).order_by(School.name).all()
    return jsonify([{"id": s.id, "name": s.name} for s in schools])

@auth_bp.route("/api/departments/<int:school_id>")
def api_departments(school_id):
    from models import Department
    depts = Department.query.filter_by(school_id=school_id).order_by(Department.name).all()
    return jsonify([{"id": d.id, "name": d.name} for d in depts])

@auth_bp.route("/api/programmes/<int:department_id>")
def api_programmes(department_id):
    from models import Programme as ProgrammeModel
    progs = ProgrammeModel.query.filter_by(department_id=department_id).order_by(ProgrammeModel.name).all()
    return jsonify([{"id": p.id, "name": p.name, "code": p.code} for p in progs])


# --- Email verification routes ---
@auth_bp.route('/check-email')
def check_email():
    return render_template('check_email.html')

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    email = verify_verification_token(token)
    if not email:
        flash('The verification link is invalid or has expired.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    stored = EmailVerificationToken.query.filter_by(
        user_id=user.id, token_hash=token_hash, used=False
    ).first()
    if not stored or stored.expires_at < datetime.utcnow():
        flash('The verification link is invalid or has expired.', 'error')
        return redirect(url_for('auth.login'))

    user.email_verified = True
    stored.used = True
    db.session.commit()
    flash('Your email has been verified! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        if user and user.role != 'admin' and not user.email_verified:
            token = generate_verification_token(email)
            send_verification_email(user, token)
        flash('If that account exists and is unverified, a new verification link has been sent.', 'success')
        return redirect(url_for('auth.login'))
    email = request.args.get('email', '')
    return render_template('resend_verification.html', email=email)


# --- Password reset ---
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()
        generic_message = (
            "If an account exists for that email address, "
            "you'll receive password reset instructions shortly."
        )
        if user:
            if not user.email_verified:
                flash('That email is not verified yet. Please verify your email first.', 'error')
                return redirect(url_for('auth.resend_verification', email=email))
            token = generate_reset_token(email)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            PasswordResetToken.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(reset_token)
            db.session.commit()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            msg = Message('Password Reset Request', recipients=[email])
            msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, simply ignore this email and no changes will be made.
'''
            try:
                mail.send(msg)
            except Exception:
                current_app.logger.exception("Failed to send password reset email to %s", email)
        flash(generic_message, 'success')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('The reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    stored_token = PasswordResetToken.query.filter_by(
        user_id=user.id, token_hash=token_hash, used=False
    ).first()
    if not stored_token or stored_token.expires_at < datetime.utcnow():
        flash('The reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        if not password or password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        user.set_password(password)
        stored_token.used = True
        db.session.commit()
        flash('Your password has been updated. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html', token=token)


# --- WebAuthn / Passkey routes ---
@auth_bp.route("/webauthn/register/begin", methods=["POST"])
@login_required
def webauthn_register_begin():
    if not WEBAUTHN_AVAILABLE:
        return jsonify({"error": "WebAuthn is not available. Please install webauthn>=2.0.0"}), 400
    
    if current_user.role == 'admin':
        return jsonify({"error": "Admin accounts cannot use passkeys."}), 400
        
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(current_user.id).encode(),
        user_name=current_user.username,
        user_display_name=current_user.full_name,
        authenticator_selection={"resident_key": "required", "user_verification": "required"},
    )
    
    session["webauthn_challenge"] = options.challenge
    return options_to_json(options)

@auth_bp.route("/webauthn/register/complete", methods=["POST"])
@login_required
def webauthn_register_complete():
    if not WEBAUTHN_AVAILABLE:
        return jsonify({"error": "WebAuthn is not available"}), 400
    
    try:
        from webauthn.helpers import parse_registration_credential_json
        credential = parse_registration_credential_json(request.get_json())
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=session.get("webauthn_challenge"),
            expected_rp_id=RP_ID,
            expected_origin=request.origin or f"https://{RP_ID}",
        )
        
        from models import WebAuthnCredential
        cred = WebAuthnCredential(
            user_id=current_user.id,
            credential_id=base64url_to_bytes(verification.credential_id).hex(),
            public_key=verification.credential_public_key.hex(),
            sign_count=verification.sign_count,
        )
        db.session.add(cred)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@auth_bp.route("/webauthn/login/begin", methods=["POST"])
def webauthn_login_begin():
    if not WEBAUTHN_AVAILABLE:
        return jsonify({"error": "WebAuthn is not available. Please install webauthn>=2.0.0"}), 400
    
    username = request.json.get("username", "").strip().lower()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    from models import WebAuthnCredential
    creds = WebAuthnCredential.query.filter_by(user_id=user.id).all()
    if not creds:
        return jsonify({"error": "No passkey registered for this account"}), 400
    
    allow_credentials = [{
        "type": "public-key",
        "id": c.credential_id,
    } for c in creds]
    
    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification="required",
    )
    session["webauthn_challenge"] = options.challenge
    session["webauthn_user_id"] = user.id
    return options_to_json(options)

@auth_bp.route("/webauthn/login/complete", methods=["POST"])
def webauthn_login_complete():
    if not WEBAUTHN_AVAILABLE:
        return jsonify({"error": "WebAuthn is not available"}), 400
    
    from webauthn.helpers import parse_authentication_credential_json
    from models import WebAuthnCredential
    try:
        credential = parse_authentication_credential_json(request.get_json())
        cred = WebAuthnCredential.query.filter_by(credential_id=credential.id).first()
        if not cred:
            return jsonify({"error": "Credential not found"}), 404
        
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=session.get("webauthn_challenge"),
            expected_rp_id=RP_ID,
            expected_origin=request.origin or f"https://{RP_ID}",
            credential_public_key=bytes.fromhex(cred.public_key),
            credential_current_sign_count=cred.sign_count,
        )
        
        cred.sign_count = verification.new_sign_count
        db.session.commit()
        
        user = User.query.get(cred.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        if not user.email_verified and user.role != 'admin':
            return jsonify({"error": "Email not verified"}), 403
            
        login_user(user)
        return jsonify({"success": True, "role": user.role})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400