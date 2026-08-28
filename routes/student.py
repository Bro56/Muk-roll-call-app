from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import random
import numpy as np
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import StudentProfile, Programme, Course, Enrollment, CourseSession, AttendanceRecord, ClassRep, LectureSession, LectureAttendance, Notification
from app_utils.face_utils import decode_base64_image, extract_face_encoding, FaceError
from app_utils.attendance_sync import record_gps_attendance
from app_utils.geo import within_check_in_range
from app_utils.checkin_queue import log_attempt, get_valid_token
from app_utils.notifications import notify_user
from app_utils.audit import log_audit
from config import Config

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "student":
        flash("That page is for students only.", "error")
        return redirect(url_for(f"{current_user.role}.dashboard"))

    classrep = ClassRep.query.filter_by(user_id=current_user.id, approved=True).first()

    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Student profile not found. Please contact admin.", "error")
        return redirect(url_for("auth.logout"))

    enrollments = Enrollment.query.filter_by(student_id=profile.id).all()
    course_rows = []
    total_present = 0
    total_sessions = 0

    for enrollment in enrollments:
        course = enrollment.course

        sessions = CourseSession.query.filter_by(course_id=course.id).filter(
            CourseSession.closed_at.isnot(None)
        ).all()
        total = len(sessions)

        if total == 0:
            present = 0
            pct = 0.0
        else:
            session_ids = [s.id for s in sessions]
            attendance_count = AttendanceRecord.query.filter(
                AttendanceRecord.session_id.in_(session_ids),
                AttendanceRecord.student_id == profile.id
            ).count()
            present = attendance_count
            pct = (present / total) * 100

        total_present += present
        total_sessions += total

        has_active_session = False
        if sessions:
            session_ids = [s.id for s in sessions]
            active_sessions = LectureSession.query.filter(
                LectureSession.course_session_id.in_(session_ids),
                LectureSession.active == True
            ).all()
            has_active_session = len(active_sessions) > 0

        course_rows.append({
            "course": course,
            "total": total,
            "present": present,
            "percentage": pct,
            "at_risk": pct < current_app.config.get("ATTENDANCE_THRESHOLD", 75) and total > 0,
            "has_active_session": has_active_session,
        })

    overall_pct = (total_present / total_sessions * 100) if total_sessions > 0 else 0

    notifications = Notification.query.filter_by(
        recipient_id=current_user.id,
        read=False
    ).order_by(Notification.created_at.desc()).all()

    return render_template(
        "student_dashboard.html",
        profile=profile,
        course_rows=course_rows,
        overall_pct=overall_pct,
        threshold=current_app.config.get("ATTENDANCE_THRESHOLD", 75),
        notifications=notifications,
        classrep=classrep,
    )


@student_bp.route("/notifications/mark-read", methods=["POST"])
@login_required
def mark_notifications_read():
    notifications = Notification.query.filter_by(
        recipient_id=current_user.id,
        read=False
    ).all()
    for notif in notifications:
        notif.read = True
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("student.dashboard"))


@student_bp.route("/choose-courses", methods=["GET", "POST"])
@login_required
def choose_courses():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Student profile not found.", "error")
        return redirect(url_for("student.dashboard"))

    if not profile.programme_id:
        flash("You don't have a programme assigned. Please contact admin.", "error")
        return redirect(url_for("student.dashboard"))

    enrolled_ids = [e.course_id for e in Enrollment.query.filter_by(student_id=profile.id).all()]

    if request.method == "POST":
        course_ids = request.form.getlist("course_ids")
        if not course_ids:
            flash("Please select at least one course.", "error")
            return redirect(url_for("student.choose_courses"))

        added_count = 0
        for course_id in course_ids:
            existing = Enrollment.query.filter_by(
                student_id=profile.id,
                course_id=int(course_id)
            ).first()
            if not existing:
                enrollment = Enrollment(
                    student_id=profile.id,
                    course_id=int(course_id)
                )
                db.session.add(enrollment)
                added_count += 1
        db.session.commit()
        flash(f"Added {added_count} course(s).", "success")
        return redirect(url_for("student.dashboard"))

    recommended_courses = Course.query.filter_by(
        programme_id=profile.programme_id
    ).order_by(Course.year_of_study, Course.name).all()

    all_courses = Course.query.order_by(Course.programme_id, Course.year_of_study, Course.name).all()

    recommended_ids = [c.id for c in recommended_courses]
    other_courses = [c for c in all_courses if c.id not in recommended_ids]

    return render_template("choose_courses.html",
                           recommended_courses=recommended_courses,
                           other_courses=other_courses,
                           enrolled_ids=enrolled_ids,
                           profile=profile)


@student_bp.route("/course/<int:course_id>")
@login_required
def course_detail(course_id):
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Student profile not found.", "error")
        return redirect(url_for("student.dashboard"))

    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(
        student_id=profile.id,
        course_id=course_id
    ).first()
    if not enrollment:
        flash("You are not enrolled in this course.", "error")
        return redirect(url_for("student.dashboard"))

    sessions = CourseSession.query.filter_by(course_id=course_id).order_by(CourseSession.date).all()
    attendance_records = AttendanceRecord.query.filter(
        AttendanceRecord.session_id.in_([s.id for s in sessions]),
        AttendanceRecord.student_id == profile.id
    ).all()
    attendance_by_session = {r.session_id: r for r in attendance_records}

    active_session = None
    attendance_taken = False
    if sessions:
        session_ids = [s.id for s in sessions]
        active_sessions = LectureSession.query.filter(
            LectureSession.course_session_id.in_(session_ids),
            LectureSession.active == True
        ).all()
        if active_sessions:
            active_session = active_sessions[0]
            existing = LectureAttendance.query.filter_by(
                lecture_session_id=active_session.id,
                student_id=profile.id
            ).first()
            if existing:
                attendance_taken = True

    return render_template("student_course_detail.html",
                           course=course,
                           sessions=sessions,
                           attendance_records=attendance_records,
                           attendance_by_session=attendance_by_session,
                           active_session=active_session,
                           attendance_taken=attendance_taken)


@student_bp.route("/qr-checkin", methods=["GET", "POST"])
@login_required
def qr_checkin():
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Student profile not found.", "error")
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        qr_code = request.form.get("qr_code", "").strip()
        if not qr_code:
            flash("Please enter or scan the QR code.", "error")
            return redirect(url_for("student.qr_checkin"))

        session = CourseSession.query.filter_by(qr_token=qr_code).first()
        if not session:
            flash("Invalid QR code. Please check with your lecturer.", "error")
            return redirect(url_for("student.qr_checkin"))

        if not session.is_open:
            flash("This QR code has expired or the session is closed.", "error")
            return redirect(url_for("student.qr_checkin"))

        existing = AttendanceRecord.query.filter_by(
            session_id=session.id,
            student_id=profile.id
        ).first()
        if existing:
            flash("You have already marked attendance for this session.", "info")
            return redirect(url_for("student.course_detail", course_id=session.course_id))

        record = AttendanceRecord(
            session_id=session.id,
            student_id=profile.id,
            status="present",
            method="qr"
        )
        db.session.add(record)
        try:
            db.session.commit()
            
            # ✅ AUDIT: Log QR check-in success
            log_audit(
                action="ATTENDANCE_MARKED",
                entity_type="attendance_record",
                entity_id=record.id,
                details=f"Student {current_user.full_name} checked in via QR for session {session.id}",
                actor=current_user
            )
        except IntegrityError:
            db.session.rollback()
        flash(f"Attendance recorded for {session.course.code} - {session.topic or 'Lecture'}! ✅", "success")
        return redirect(url_for("student.course_detail", course_id=session.course_id))

    return render_template("qr_checkin.html")


@student_bp.route("/verify-face", methods=["POST"])
@login_required
def verify_face():
    data = request.get_json()
    if not data or 'face_image' not in data:
        return jsonify({'success': False, 'message': 'No face image provided'})

    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({'success': False, 'message': 'Student profile not found'})

    if profile.face_encoding is None:
        return jsonify({'success': False, 'message': 'No face enrolled. Please contact admin to enroll your face.'})

    try:
        rgb_array, pil_image = decode_base64_image(data['face_image'])
        captured_encoding, _ = extract_face_encoding(rgb_array)
        stored_encoding = np.array(profile.face_encoding)
        distance = np.linalg.norm(captured_encoding - stored_encoding)
        threshold = 0.5

        if distance <= threshold:
            confidence = max(0.0, 1.0 - (distance / threshold))
            return jsonify({
                'success': True,
                'message': f'Face verified with {confidence:.0%} confidence',
                'confidence': confidence,
                'session_id': data.get('session_id')
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Face does not match. Please try again.'
            })

    except FaceError as e:
        return jsonify({'success': False, 'message': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error verifying face: {str(e)}'})


@student_bp.route("/lecture-session/<int:session_id>/attend", methods=["POST"])
@login_required
def attend_lecture_session(session_id):
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Student profile not found.", "error")
        return redirect(url_for("student.dashboard"))

    lecture_session = LectureSession.query.filter_by(id=session_id, active=True).first()
    if not lecture_session:
        flash("No active session for this lecture. Please contact your class rep.", "warning")
        return redirect(url_for("student.dashboard"))

    existing = LectureAttendance.query.filter_by(
        lecture_session_id=session_id, student_id=profile.id
    ).first()
    if existing:
        flash("You have already marked attendance for this lecture.", "info")
        return redirect(request.referrer or url_for("student.dashboard"))

    lat = request.form.get("latitude")
    lon = request.form.get("longitude")
    accuracy = request.form.get("accuracy")

    if not lat or not lon:
        log_attempt(lecture_session, profile, success=False, failure_reason="gps_missing")
        
        # ✅ AUDIT: Log failed GPS attempt
        log_audit(
            action="ATTENDANCE_FAILED",
            entity_type="lecture_session",
            entity_id=session_id,
            details=f"Student {current_user.full_name} failed GPS check-in: GPS missing",
            actor=current_user
        )
        
        flash("Could not get your location. Please allow location access and try again.", "error")
        return redirect(request.referrer or url_for("student.dashboard"))

    try:
        lat = float(lat)
        lon = float(lon)
        accuracy = float(accuracy) if accuracy else None
    except ValueError:
        log_attempt(lecture_session, profile, success=False, failure_reason="gps_missing")
        
        # ✅ AUDIT: Log invalid location data
        log_audit(
            action="ATTENDANCE_FAILED",
            entity_type="lecture_session",
            entity_id=session_id,
            details=f"Student {current_user.full_name} failed GPS check-in: Invalid location data",
            actor=current_user
        )
        
        flash("Invalid location data. Please try again.", "error")
        return redirect(request.referrer or url_for("student.dashboard"))

    rep_lat = lecture_session.latitude
    rep_lon = lecture_session.longitude
    rep_accuracy = lecture_session.rep_accuracy_metres

    within_range, _distance, _radius = within_check_in_range(
        rep_lat, rep_lon, rep_accuracy,
        lat, lon, accuracy,
        Config.GPS_BASE_RADIUS_METRES, Config.GPS_MAX_ACCURACY_BUFFER_METRES,
    )
    if not within_range:
        log_attempt(lecture_session, profile, success=False, failure_reason="gps_out_of_range")
        
        # ✅ AUDIT: Log out-of-range attempt
        log_audit(
            action="ATTENDANCE_FAILED",
            entity_type="lecture_session",
            entity_id=session_id,
            details=f"Student {current_user.full_name} failed GPS check-in: Out of range (lat={lat}, lon={lon})",
            actor=current_user
        )
        
        messages = [
            "You seem to be just outside the check-in area — move a little closer and try again.",
            "Go attend lectures or you won't graduate. 🎓 (Also: move closer and retry!)",
            "Your location doesn't quite match the lecture hall yet — try again in a moment.",
            "We couldn't confirm you're in range. Get a bit closer to the front and retry.",
            "Almost there! Move a little closer to the lecture hall and try again. 📚",
        ]
        flash(random.choice(messages), "error")
        return redirect(request.referrer or url_for("student.dashboard"))

    face_image = request.form.get("face_image")
    if not face_image:
        log_attempt(lecture_session, profile, success=False, failure_reason="face_missing")
        
        # ✅ AUDIT: Log missing face
        log_audit(
            action="ATTENDANCE_FAILED",
            entity_type="lecture_session",
            entity_id=session_id,
            details=f"Student {current_user.full_name} failed face verification: Face image missing",
            actor=current_user
        )
        
        flash("We couldn't get a photo from your camera. Check camera permissions and try again.", "error")
        return redirect(request.referrer or url_for("student.dashboard"))
    
    if profile.face_encoding is None:
        log_attempt(lecture_session, profile, success=False, failure_reason="no_face_enrolled")
        
        # ✅ AUDIT: Log no face enrolled
        log_audit(
            action="ATTENDANCE_FAILED",
            entity_type="lecture_session",
            entity_id=session_id,
            details=f"Student {current_user.full_name} failed face verification: No face enrolled",
            actor=current_user
        )
        
        flash("No face enrolled on your account. Contact admin to enroll your face.", "error")
        return redirect(request.referrer or url_for("student.dashboard"))

    try:
        rgb_array, _ = decode_base64_image(face_image)
        captured_encoding, _ = extract_face_encoding(rgb_array)
    except FaceError as e:
        log_attempt(lecture_session, profile, success=False, failure_reason="face_error")
        
        # ✅ AUDIT: Log face extraction error
        log_audit(
            action="ATTENDANCE_FAILED",
            entity_type="lecture_session",
            entity_id=session_id,
            details=f"Student {current_user.full_name} failed face verification: {str(e)}",
            actor=current_user
        )
        
        flash(str(e), "error")
        return redirect(request.referrer or url_for("student.dashboard"))

    stored_encoding = np.array(profile.face_encoding)
    face_distance = np.linalg.norm(captured_encoding - stored_encoding)
    if face_distance > Config.FACE_MATCH_TOLERANCE:
        log_attempt(lecture_session, profile, success=False, failure_reason="face_no_match")
        
        # ✅ AUDIT: Log face mismatch
        log_audit(
            action="ATTENDANCE_FAILED",
            entity_type="lecture_session",
            entity_id=session_id,
            details=f"Student {current_user.full_name} failed face verification: Face mismatch (distance={face_distance:.4f})",
            actor=current_user
        )
        
        flash("Face didn't match your enrolled photo. Try again with good lighting, facing the camera directly.", "error")
        return redirect(request.referrer or url_for("student.dashboard"))

    # ✅ SUCCESS: Log attempt and record attendance
    log_attempt(lecture_session, profile, success=True, method="auto")
    record_gps_attendance(lecture_session, profile, status="present")

    # ✅ AUDIT: Log successful check-in
    log_audit(
        action="ATTENDANCE_MARKED",
        entity_type="lecture_session",
        entity_id=session_id,
        details=f"Student {current_user.full_name} successfully checked in via GPS+Face for session {session_id}",
        actor=current_user
    )

    # Deduplicated notification
    notify_user(
        recipient_id=current_user.id,
        message=f"✅ Attendance recorded for {lecture_session.course_session.course.code} - {lecture_session.course_session.topic or 'Lecture'}!",
        link=url_for('student.course_detail', course_id=lecture_session.course_session.course_id),
        dedup_hours=1
    )

    flash("✅ Attendance recorded successfully! You're now marked present.", "success")
    return redirect(request.referrer or url_for("student.dashboard"))


@student_bp.route("/rectify/<token>")
@login_required
def rectify_scan(token):
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    rectify_token = get_valid_token(token)

    if not rectify_token:
        return render_template("rectify_confirm.html", error="This code has expired or was already used. Ask your class rep to generate a new one.")

    if not profile or rectify_token.student_id != profile.id:
        return render_template("rectify_confirm.html", error="This code isn't for your account. Please log in as yourself and ask your class rep to generate a new code for you.")

    seconds_left = max(0, int((rectify_token.expires_at - datetime.utcnow()).total_seconds()))
    return render_template("rectify_confirm.html", token=token, seconds_left=seconds_left)


@student_bp.route("/rectify/<token>/confirm", methods=["POST"])
@login_required
def rectify_confirm(token):
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    rectify_token = get_valid_token(token)

    if not rectify_token:
        return jsonify({"success": False, "message": "This code has expired or was already used."})
    if not profile or rectify_token.student_id != profile.id:
        return jsonify({"success": False, "message": "This code isn't for your account."})

    face_image = request.form.get("face_image") or (request.get_json(silent=True) or {}).get("face_image")
    if not face_image:
        return jsonify({"success": False, "message": "We couldn't get a photo from your camera. Check camera permissions."})
    if profile.face_encoding is None:
        return jsonify({"success": False, "message": "No face enrolled on your account. Contact admin."})

    try:
        rgb_array, _ = decode_base64_image(face_image)
        captured_encoding, _ = extract_face_encoding(rgb_array)
    except FaceError as e:
        return jsonify({"success": False, "message": str(e)})

    stored_encoding = np.array(profile.face_encoding)
    face_distance = np.linalg.norm(captured_encoding - stored_encoding)
    if face_distance > Config.FACE_MATCH_TOLERANCE:
        return jsonify({"success": False, "message": "Face didn't match your enrolled photo. Try again with good lighting."})

    lecture_session = rectify_token.lecture_session

    existing = LectureAttendance.query.filter_by(
        lecture_session_id=lecture_session.id, student_id=profile.id
    ).first()
    if not existing:
        log_attempt(lecture_session, profile, success=True, method="rectify")
        record_gps_attendance(lecture_session, profile, status="present")
        
        # ✅ AUDIT: Log rectify token usage
        log_audit(
            action="RECTIFY_USED",
            entity_type="rectify_token",
            entity_id=rectify_token.id,
            details=f"Student {current_user.full_name} used rectify token for session {lecture_session.id}",
            actor=current_user
        )

    rectify_token.used_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"success": True, "message": "You're marked present. You can close this page."})


@student_bp.route("/check-classrep-status")
@login_required
def check_classrep_status():
    classrep = ClassRep.query.filter_by(user_id=current_user.id, approved=True).first()
    return jsonify({
        "is_class_rep": classrep is not None,
        "approved": classrep.approved if classrep else False,
        "has_applied": ClassRep.query.filter_by(user_id=current_user.id).first() is not None
    })