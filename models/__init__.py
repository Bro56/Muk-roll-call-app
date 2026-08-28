import datetime
import secrets

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def now_utc():
    return datetime.datetime.utcnow()


# ---------------------------------------------------------------------------
# Academic hierarchy: College -> School -> Department -> Programme -> Course
# ---------------------------------------------------------------------------

class College(db.Model):
    __tablename__ = "colleges"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False, unique=True)

    schools = db.relationship("School", backref="college", cascade="all, delete-orphan",
                               order_by="School.name")


class School(db.Model):
    __tablename__ = "schools"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20))

    departments = db.relationship("Department", backref="school", cascade="all, delete-orphan",
                                   order_by="Department.name")


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20))

    programmes = db.relationship("Programme", backref="department", cascade="all, delete-orphan",
                                  order_by="Programme.name")


class Programme(db.Model):
    __tablename__ = "programmes"
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20))
    degree_level = db.Column(db.String(50), default="Bachelors")

    courses = db.relationship("Course", backref="programme", cascade="all, delete-orphan",
                               order_by="Course.year_of_study, Course.name")
    students = db.relationship("StudentProfile", backref="programme")


class Course(db.Model):
    __tablename__ = "courses"
    __table_args__ = (
        db.Index("ix_courses_code", "code"),
        db.Index("ix_courses_name", "name"),
        db.Index("ix_courses_programme_id", "programme_id"),
        db.Index("ix_courses_lecturer_id", "lecturer_id"),
    )
    id = db.Column(db.Integer, primary_key=True)
    programme_id = db.Column(db.Integer, db.ForeignKey("programmes.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    year_of_study = db.Column(db.Integer, default=1)
    semester = db.Column(db.Integer, default=1)
    lecturer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    sessions = db.relationship("CourseSession", backref="course", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", backref="course", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = "users"
    __table_args__ = (
        db.Index("ix_users_username", "username"),
        db.Index("ix_users_email", "email"),
        db.Index("ix_users_role", "role"),
        db.Index("ix_users_created_at", "created_at"),
    )
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)
    theme_preference = db.Column(db.String(10), default="light")
    email_verified = db.Column(db.Boolean, default=False)

    student_profile = db.relationship("StudentProfile", backref="user", uselist=False,
                                       cascade="all, delete-orphan")
    lecturer_courses = db.relationship("Course", backref="lecturer")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"
    __table_args__ = (
        db.Index("ix_student_profiles_user_id", "user_id"),
        db.Index("ix_student_profiles_programme_id", "programme_id"),
        db.Index("ix_student_profiles_reg_no", "registration_number"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    student_number = db.Column(db.String(50), unique=True)
    registration_number = db.Column(db.String(50), unique=True)
    programme_id = db.Column(db.Integer, db.ForeignKey("programmes.id"), nullable=True)
    year_of_study = db.Column(db.Integer, default=1)
    face_encoding = db.Column(db.PickleType, nullable=True)
    face_photo_path = db.Column(db.String(255), nullable=True)
    face_enrolled_at = db.Column(db.DateTime, nullable=True)

    enrollments = db.relationship("Enrollment", backref="student", cascade="all, delete-orphan")


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=now_utc)

    __table_args__ = (db.UniqueConstraint("student_id", "course_id", name="uq_student_course"),)


# ---------------------------------------------------------------------------
# Roll call sessions + attendance
# ---------------------------------------------------------------------------

class CourseSession(db.Model):
    __tablename__ = "course_sessions"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    date = db.Column(db.Date, default=lambda: now_utc().date())
    topic = db.Column(db.String(255))
    opened_at = db.Column(db.DateTime, default=now_utc)
    closed_at = db.Column(db.DateTime, nullable=True)
    qr_token = db.Column(db.String(64), unique=True, default=lambda: secrets.token_urlsafe(24))
    qr_expires_at = db.Column(db.DateTime, nullable=True)

    records = db.relationship("AttendanceRecord", backref="session", cascade="all, delete-orphan")

    @property
    def is_open(self):
        return self.closed_at is None


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("course_sessions.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False)
    status = db.Column(db.String(10), default="present")
    method = db.Column(db.String(10), default="manual")
    marked_at = db.Column(db.DateTime, default=now_utc)
    confidence = db.Column(db.Float, nullable=True)

    __table_args__ = (db.UniqueConstraint("session_id", "student_id", name="uq_session_student"),)


# ===========================================================================
# Class Representatives, Location-based Sessions, Notifications
# ===========================================================================

class ClassRep(db.Model):
    __tablename__ = 'class_reps'
    __table_args__ = (
        db.Index("ix_class_reps_user_id", "user_id"),
        db.Index("ix_class_reps_programme_id", "programme_id"),
        db.Index("ix_class_reps_approved", "approved"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    programme_id = db.Column(db.Integer, db.ForeignKey('programmes.id'), nullable=False)
    approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc)

    user = db.relationship('User', foreign_keys=[user_id], backref='classrep')
    programme = db.relationship('Programme')
    approver = db.relationship('User', foreign_keys=[approved_by])


class LectureSession(db.Model):
    __tablename__ = 'lecture_sessions'
    __table_args__ = (
        db.Index("ix_lecture_sessions_active", "active"),
        db.Index("ix_lecture_sessions_course_session_id", "course_session_id"),
        db.Index("ix_lecture_sessions_started_by", "started_by_user_id"),
    )
    id = db.Column(db.Integer, primary_key=True)
    course_session_id = db.Column(db.Integer, db.ForeignKey('course_sessions.id'), nullable=False)
    class_rep_id = db.Column(db.Integer, db.ForeignKey('class_reps.id'), nullable=True)
    started_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_by_role = db.Column(db.String(10), nullable=False, default='class_rep')
    started_at = db.Column(db.DateTime, default=now_utc)
    ended_at = db.Column(db.DateTime, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    rep_accuracy_metres = db.Column(db.Float, nullable=True)
    radius_metres = db.Column(db.Float, default=40.0)
    active = db.Column(db.Boolean, default=True)

    course_session = db.relationship('CourseSession', backref='lecture_sessions')
    class_rep = db.relationship('ClassRep')
    started_by = db.relationship('User', foreign_keys=[started_by_user_id])

    @property
    def started_by_name(self):
        return self.started_by.full_name if self.started_by else "Unknown"

    @property
    def started_by_label(self):
        return "Lecturer" if self.started_by_role == "lecturer" else "Class Rep"


class LectureAttendance(db.Model):
    __tablename__ = 'lecture_attendances'
    id = db.Column(db.Integer, primary_key=True)
    lecture_session_id = db.Column(db.Integer, db.ForeignKey('lecture_sessions.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    status = db.Column(db.String(10), default='present')
    timestamp = db.Column(db.DateTime, default=now_utc)
    gps_accuracy = db.Column(db.Float, nullable=True)
    face_verified = db.Column(db.Boolean, default=True)

    lecture_session = db.relationship('LectureSession', backref='attendances')
    student = db.relationship('StudentProfile')


class CheckInAttempt(db.Model):
    __tablename__ = 'checkin_attempts'
    __table_args__ = (
        db.Index("ix_checkin_attempts_session_student", "lecture_session_id", "student_id"),
        db.Index("ix_checkin_attempts_success", "success"),
    )
    id = db.Column(db.Integer, primary_key=True)
    lecture_session_id = db.Column(db.Integer, db.ForeignKey('lecture_sessions.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(10), default='auto')
    success = db.Column(db.Boolean, nullable=False)
    failure_reason = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc)

    lecture_session = db.relationship('LectureSession', backref='checkin_attempts')
    student = db.relationship('StudentProfile')


class RectifyToken(db.Model):
    __tablename__ = 'rectify_tokens'
    id = db.Column(db.Integer, primary_key=True)
    lecture_session_id = db.Column(db.Integer, db.ForeignKey('lecture_sessions.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    class_rep_id = db.Column(db.Integer, db.ForeignKey('class_reps.id'), nullable=True)
    issued_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(48), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc)

    lecture_session = db.relationship('LectureSession')
    student = db.relationship('StudentProfile')
    class_rep = db.relationship('ClassRep')
    issued_by = db.relationship('User')

    @property
    def is_expired(self):
        return now_utc() > self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None


class Notification(db.Model):
    __tablename__ = 'notifications'
    __table_args__ = (
        db.Index("ix_notifications_recipient_read", "recipient_id", "read"),
        db.Index("ix_notifications_created_at", "created_at"),
    )
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now_utc)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    recipient = db.relationship('User')


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(128), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now_utc)

    user = db.relationship('User')


class EmailVerificationToken(db.Model):
    __tablename__ = 'email_verification_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.String(128), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=now_utc)

    user = db.relationship('User')


class WebAuthnCredential(db.Model):
    __tablename__ = 'webauthn_credentials'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    credential_id = db.Column(db.String(255), nullable=False, unique=True)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=now_utc)

    user = db.relationship('User')


# ===========================================================================
# Lecturer Activation Codes (gated signup)
# ===========================================================================

class LecturerActivationCode(db.Model):
    __tablename__ = 'lecturer_activation_codes'
    __table_args__ = (
        db.Index("ix_lecturer_codes_code", "code"),
        db.Index("ix_lecturer_codes_used_at", "used_at"),
        db.Index("ix_lecturer_codes_is_active", "is_active"),
    )
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=now_utc)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    creator = db.relationship('User', foreign_keys=[created_by])
    redeemer = db.relationship('User', foreign_keys=[used_by])

    @property
    def is_expired(self):
        return now_utc() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and self.used_at is None and not self.is_expired


# ===========================================================================
# Audit Trail (who did what, when, from which IP)
# ===========================================================================

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    __table_args__ = (
        db.Index("ix_audit_logs_actor_id", "actor_id"),
        db.Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        db.Index("ix_audit_logs_created_at", "created_at"),
    )
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc)

    actor = db.relationship('User')