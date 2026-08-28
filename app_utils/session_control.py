"""
app_utils/session_control.py
Session control utilities with deduplicated notifications and audit logging.
"""

from extensions import db
from models import LectureSession, CheckInAttempt, Notification, User
from app_utils.notifications import notify_user, notify_admins
from app_utils.audit import log_audit as _base_log_audit
from datetime import datetime


# ---------------------------------------------------------------------------
# Backward-compatible audit wrapper
# ---------------------------------------------------------------------------
def log_audit(actor=None, actor_id=None, **kwargs):
    """
    Audit logger that accepts either a User object (actor) or a raw actor_id.
    All other keyword arguments are forwarded to the underlying audit logger.
    """
    if actor is not None and actor_id is None:
        actor_id = getattr(actor, "id", None)
        if actor_id is None:
            raise ValueError("actor object has no 'id' attribute")

    if actor_id is None:
        raise ValueError("Either actor or actor_id must be provided")

    return _base_log_audit(actor_id=actor_id, **kwargs)


# ---------------------------------------------------------------------------
# Permission helper
# ---------------------------------------------------------------------------
def can_manage_course(user, course):
    """
    Return True if *user* is allowed to manage *course*.
    Admins can manage any course; lecturers can manage only their own.
    """
    if not user or not course:
        return False

    role = getattr(user, "role", None)
    user_id = getattr(user, "id", None)

    # Global admin override
    if role == "admin":
        return True

    # Lecturer checks (handles both FK and many-to-many)
    if role == "lecturer":
        if getattr(course, "lecturer_id", None) == user_id:
            return True

        course_lecturers = getattr(course, "lecturers", None)
        if course_lecturers:
            lecturer_ids = [getattr(lect, "id", lect) for lect in course_lecturers]
            if user_id in lecturer_ids:
                return True

    return False


# ---------------------------------------------------------------------------
# NEW: Class-rep check-in status helper
# ---------------------------------------------------------------------------
def rep_has_checked_in(lecture_session_id, rep_id):
    """
    Return True if the class representative (rep_id) has already
    successfully checked in to the given lecture session.
    """
    if not lecture_session_id or not rep_id:
        return False

    attempt = CheckInAttempt.query.filter_by(
        lecture_session_id=lecture_session_id,
        student_id=rep_id,
        success=True
    ).first()

    return attempt is not None


# ---------------------------------------------------------------------------
# Convenience wrapper for routes/lecturer.py
# ---------------------------------------------------------------------------
def start_gps_session(course_session_id, current_user, gps_lat, gps_lng, gps_radius=100):
    """
    Start a lecture session using a User object instead of a raw user id.
    """
    if current_user is None:
        raise ValueError("current_user is required")

    starter_user_id = getattr(current_user, "id", None)
    if starter_user_id is None:
        raise ValueError("current_user must have an 'id' attribute")

    return start_lecture_session(
        course_session_id=course_session_id,
        starter_user_id=starter_user_id,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        gps_radius=gps_radius,
    )


# ---------------------------------------------------------------------------
# Existing session control functions (unchanged)
# ---------------------------------------------------------------------------
def start_lecture_session(course_session_id, starter_user_id, gps_lat, gps_lng, gps_radius=100):
    """
    Start a new lecture session with GPS anchor point.
    Notifies enrolled students and logs the action.
    """
    from models import CourseSession, StudentProfile

    course_session = CourseSession.query.get_or_404(course_session_id)

    # Check if session already active
    existing = LectureSession.query.filter_by(
        course_session_id=course_session_id,
        active=True
    ).first()

    if existing:
        return existing, False  # Already active

    session = LectureSession(
        course_session_id=course_session_id,
        started_by_user_id=starter_user_id,
        gps_latitude=gps_lat,
        gps_longitude=gps_lng,
        gps_radius_meters=gps_radius,
        active=True,
        started_at=datetime.utcnow()
    )
    db.session.add(session)
    db.session.commit()

    # Audit log
    log_audit(
        actor_id=starter_user_id,
        action="lecture_session.start",
        entity_type="LectureSession",
        entity_id=session.id,
        details={
            "course": course_session.course.name if course_session.course else None,
            "gps": f"{gps_lat}, {gps_lng}",
            "radius": gps_radius
        }
    )

    # Notify enrolled students (deduplicated per student)
    enrolled = StudentProfile.query.filter_by(programme_id=course_session.course.programme_id).all()
    for student in enrolled:
        notify_user(
            recipient_id=student.user_id,
            title="Lecture Session Started",
            message=f"A new session for {course_session.course.name} has started. Check in now!",
            notification_type="info",
            link=f"/student/checkin/{session.id}",
            dedup_window_minutes=5
        )

    return session, True


def end_lecture_session(session_id, ended_by_user_id):
    """End a lecture session and log the action."""
    session = LectureSession.query.get_or_404(session_id)
    session.active = False
    session.ended_at = datetime.utcnow()
    session.ended_by_user_id = ended_by_user_id
    db.session.commit()

    log_audit(
        actor_id=ended_by_user_id,
        action="lecture_session.end",
        entity_type="LectureSession",
        entity_id=session.id,
        details={"duration_minutes": (session.ended_at - session.started_at).total_seconds() / 60 if session.started_at else None}
    )

    return session


def record_checkin(lecture_session_id, student_id, gps_lat, gps_lng, method="gps"):
    """
    Record a student check-in with GPS verification.
    Returns (attempt, success_boolean, distance_meters).
    """
    from math import radians, sin, cos, sqrt, atan2

    session = LectureSession.query.get_or_404(lecture_session_id)

    if not session.active:
        attempt = CheckInAttempt(
            lecture_session_id=lecture_session_id,
            student_id=student_id,
            success=False,
            failure_reason="Session not active",
            created_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
        return attempt, False, None

    # Haversine distance calculation
    R = 6371000  # Earth radius in meters
    lat1, lon1 = radians(session.gps_latitude), radians(session.gps_longitude)
    lat2, lon2 = radians(gps_lat), radians(gps_lng)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    success = distance <= session.gps_radius_meters

    attempt = CheckInAttempt(
        lecture_session_id=lecture_session_id,
        student_id=student_id,
        gps_latitude=gps_lat,
        gps_longitude=gps_lng,
        distance_meters=round(distance, 2),
        success=success,
        failure_reason=None if success else f"Outside radius ({round(distance, 1)}m > {session.gps_radius_meters}m)",
        checkin_method=method,
        created_at=datetime.utcnow()
    )
    db.session.add(attempt)
    db.session.commit()

    if success:
        notify_user(
            recipient_id=student_id,
            title="Attendance Recorded",
            message="Your attendance has been successfully recorded.",
            notification_type="success",
            dedup_window_minutes=60
        )

    return attempt, success, distance