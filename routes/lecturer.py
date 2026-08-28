import io
from datetime import datetime

from flask import (
    Blueprint, render_template, jsonify, send_file, request, redirect, url_for, flash
)
from flask_login import login_required, current_user

from extensions import db
from models import Course, CourseSession, LectureSession
from app_utils.stats import course_roster_stats
from app_utils.report_utils import build_attendance_csv, build_attendance_pdf
from app_utils.attendance_sync import close_gps_session
from app_utils.session_control import can_manage_course, start_gps_session
from app_utils.checkin_queue import needs_attention_for_course
from app_utils.audit import log_audit
from config import Config

lecturer_bp = Blueprint("lecturer", __name__, url_prefix="/lecturer")


def _require_lecturer():
    if current_user.role != "lecturer":
        flash("That page is only available to lecturers.", "error")
        return redirect(url_for(f"{current_user.role}.dashboard"))
    return None


def _own_course_or_404(course_id):
    course = Course.query.get_or_404(course_id)
    if course.lecturer_id != current_user.id:
        flash("You are not assigned to that course.", "error")
        return None
    return course


def _active_lecture_session_for_course(course_id):
    return (
        db.session.query(LectureSession)
        .join(CourseSession, LectureSession.course_session_id == CourseSession.id)
        .filter(CourseSession.course_id == course_id, LectureSession.active.is_(True))
        .first()
    )


@lecturer_bp.route("/dashboard")
@login_required
def dashboard():
    guard = _require_lecturer()
    if guard:
        return guard
    courses = Course.query.filter_by(lecturer_id=current_user.id).order_by(Course.code).all()
    cards = []
    for c in courses:
        roster = course_roster_stats(c)
        avg = sum(r["percentage"] for r in roster) / len(roster) if roster else 0.0
        live_session = _active_lecture_session_for_course(c.id)
        cards.append({
            "course": c, "enrolled": len(roster), "avg_attendance": avg,
            "live_session": live_session,
        })
    return render_template("lecturer_dashboard.html", cards=cards)


@lecturer_bp.route("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    guard = _require_lecturer()
    if guard:
        return guard
    course = _own_course_or_404(course_id)
    if not course:
        return redirect(url_for("lecturer.dashboard"))

    roster = course_roster_stats(course)
    course_sessions = CourseSession.query.filter_by(course_id=course_id).order_by(
        CourseSession.date.desc(), CourseSession.id.desc()
    ).all()
    live_session = _active_lecture_session_for_course(course_id)
    needs_attention = needs_attention_for_course(course_id) if live_session else []

    return render_template(
        "lecturer_course_detail.html",
        course=course, roster=roster, course_sessions=course_sessions,
        live_session=live_session, threshold=Config.ATTENDANCE_THRESHOLD,
        needs_attention=needs_attention,
        radius_metres=Config.GPS_BASE_RADIUS_METRES,
        rep_accuracy_warn=Config.GPS_REP_ACCURACY_WARN_METRES,
        rectify_ttl=Config.RECTIFY_TOKEN_TTL_SECONDS,
    )


@lecturer_bp.route("/course/<int:course_id>/create-session", methods=["POST"])
@login_required
def create_course_session(course_id):
    guard = _require_lecturer()
    if guard:
        return guard
    course = _own_course_or_404(course_id)
    if not course:
        return redirect(url_for("lecturer.dashboard"))

    existing_count = CourseSession.query.filter_by(course_id=course_id).count()
    topic = request.form.get("topic", "").strip() or f"{course.code} - Session {existing_count + 1}"

    course_session = CourseSession(course_id=course_id, topic=topic, date=datetime.utcnow().date())
    db.session.add(course_session)
    db.session.commit()

    # ✅ AUDIT: Log session creation
    log_audit(
        action="SESSION_CREATED",
        entity_type="course_session",
        entity_id=course_session.id,
        details=f"Lecturer {current_user.full_name} created session '{topic}' for course {course.code}",
        actor=current_user
    )

    flash(f'New session "{topic}" created. Click "Start" on it when the lecture begins.', "success")
    return redirect(url_for("lecturer.course_detail", course_id=course_id))


@lecturer_bp.route("/course-session/<int:session_id>/start", methods=["POST"])
@login_required
def start_session(session_id):
    guard = _require_lecturer()
    if guard:
        return guard

    course_session = CourseSession.query.get_or_404(session_id)
    course = _own_course_or_404(course_session.course_id)
    if not course:
        return redirect(url_for("lecturer.dashboard"))

    lat = request.form.get("latitude")
    lon = request.form.get("longitude")
    accuracy = request.form.get("accuracy")
    if not lat or not lon:
        flash("Could not get your location. Please allow location access.", "error")
        return redirect(url_for("lecturer.course_detail", course_id=course.id))

    try:
        lat = float(lat)
        lon = float(lon)
        accuracy = float(accuracy) if accuracy else None
    except ValueError:
        flash("Invalid location data.", "error")
        return redirect(url_for("lecturer.course_detail", course_id=course.id))

    lecture_session, error = start_gps_session(course_session, current_user, lat, lon, accuracy)
    if error:
        flash(error, "warning")
        return redirect(url_for("lecturer.course_detail", course_id=course.id))

    # ✅ AUDIT: Log session start
    log_audit(
        action="SESSION_STARTED",
        entity_type="lecture_session",
        entity_id=lecture_session.id,
        details=f"Lecturer {current_user.full_name} started session for course {course.code} at lat={lat}, lon={lon}",
        actor=current_user
    )

    flash("Lecture session started! Students nearby can now mark attendance.", "success")
    return redirect(url_for("lecturer.course_detail", course_id=course.id))


@lecturer_bp.route("/session/<int:session_id>/end", methods=["POST"])
@login_required
def end_session(session_id):
    guard = _require_lecturer()
    if guard:
        return guard

    lecture_session = LectureSession.query.get_or_404(session_id)
    course = lecture_session.course_session.course
    if not can_manage_course(current_user, course):
        flash("You are not authorised to end this session.", "error")
        return redirect(url_for("lecturer.dashboard"))

    if not lecture_session.active:
        flash("This session is already ended.", "warning")
        return redirect(url_for("lecturer.course_detail", course_id=course.id))

    # Calculate duration for audit
    duration_minutes = None
    if lecture_session.started_at:
        duration = datetime.utcnow() - lecture_session.started_at
        duration_minutes = int(duration.total_seconds() / 60)

    close_gps_session(lecture_session)

    # ✅ AUDIT: Log session end with duration
    log_audit(
        action="SESSION_ENDED",
        entity_type="lecture_session",
        entity_id=session_id,
        details=f"Lecturer {current_user.full_name} ended session for course {course.code} (duration: {duration_minutes} minutes)",
        actor=current_user
    )

    flash("Lecture session ended. Attendance has been recorded.", "success")
    return redirect(url_for("lecturer.course_detail", course_id=course.id))


@lecturer_bp.route("/courses/<int:course_id>/export/<fmt>")
@login_required
def export_report(course_id, fmt):
    guard = _require_lecturer()
    if guard:
        return guard
    course = _own_course_or_404(course_id)
    if not course:
        return redirect(url_for("lecturer.dashboard"))

    roster = course_roster_stats(course)

    # ✅ AUDIT: Log export
    log_audit(
        action="EXPORT_REPORT",
        entity_type="course",
        entity_id=course_id,
        details=f"Lecturer {current_user.full_name} exported {fmt} report for {course.code}",
        actor=current_user
    )

    if fmt == "csv":
        content = build_attendance_csv(course, roster)
        return send_file(
            io.BytesIO(content), mimetype="text/csv", as_attachment=True,
            download_name=f"{course.code}_attendance.csv",
        )
    elif fmt == "pdf":
        content = build_attendance_pdf(course, roster, threshold=Config.ATTENDANCE_THRESHOLD)
        return send_file(
            io.BytesIO(content), mimetype="application/pdf", as_attachment=True,
            download_name=f"{course.code}_attendance.pdf",
        )
    flash("Unknown export format.", "error")
    return redirect(url_for("lecturer.course_detail", course_id=course_id))


@lecturer_bp.route("/courses/<int:course_id>/gps-status")
@login_required
def gps_status(course_id):
    guard = _require_lecturer()
    if guard:
        return jsonify({"error": "forbidden"}), 403
    course = _own_course_or_404(course_id)
    if not course:
        return jsonify({"error": "forbidden"}), 403

    active_session = _active_lecture_session_for_course(course_id)

    if not active_session:
        return jsonify({"active": False})

    checked_in = len(active_session.attendances)

    return jsonify({
        "active": True,
        "started_at": active_session.started_at.strftime("%H:%M"),
        "radius_metres": active_session.radius_metres,
        "checked_in_count": checked_in,
        "total_enrolled": len(course.enrollments),
        "started_by": active_session.started_by_name,
        "started_by_role": active_session.started_by_label,
    })