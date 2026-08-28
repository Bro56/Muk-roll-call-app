from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from extensions import db
from models import (
    User, StudentProfile, Programme, ClassRep, CourseSession,
    LectureSession, LectureAttendance, Course,
    Enrollment, AttendanceRecord
)
from app_utils.attendance_sync import close_gps_session
from app_utils.checkin_queue import needs_attention_for_course, needs_attention_for_programme, create_rectify_token
from app_utils.qr_utils import generate_qr_data_url
from app_utils.session_control import can_manage_course, start_gps_session, rep_has_checked_in
from app_utils.notifications import notify_admins
from config import Config

class_rep_bp = Blueprint('class_rep', __name__, url_prefix='/class-rep')


def _require_approved_classrep():
    """Returns the ClassRep record for the current user, or None (with a flash
    message already queued) if they aren't an approved class rep."""
    classrep = ClassRep.query.filter_by(user_id=current_user.id, approved=True).first()
    if not classrep:
        flash('You are not an approved class representative.', 'error')
        return None
    return classrep


@class_rep_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Only students can access this area.', 'error')
        return redirect(url_for('student.dashboard'))

    classrep = ClassRep.query.filter_by(user_id=current_user.id).first()
    if not classrep:
        flash('You are not registered as a class representative. Contact admin.', 'error')
        return redirect(url_for('student.dashboard'))

    courses = Course.query.filter_by(
        programme_id=classrep.programme_id
    ).order_by(Course.year_of_study, Course.name).all()

    course_ids = [c.id for c in courses]
    active_session = None
    if course_ids:
        active_session = (
            db.session.query(LectureSession)
            .join(CourseSession, LectureSession.course_session_id == CourseSession.id)
            .filter(CourseSession.course_id.in_(course_ids), LectureSession.active.is_(True))
            .first()
        )

    attention_total, _ = needs_attention_for_programme(classrep.programme_id)

    return render_template('class_rep_dashboard.html',
                            classrep=classrep,
                            courses=courses,
                            active_session=active_session,
                            attention_total=attention_total,
                            radius_metres=Config.GPS_BASE_RADIUS_METRES)


@class_rep_bp.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    classrep = _require_approved_classrep()
    if not classrep:
        return redirect(url_for('student.dashboard'))

    course = Course.query.get_or_404(course_id)

    if course.programme_id != classrep.programme_id:
        flash('This course is not in your programme.', 'error')
        return redirect(url_for('class_rep.dashboard'))

    course_sessions = CourseSession.query.filter_by(course_id=course_id).order_by(
        CourseSession.date.desc(), CourseSession.id.desc()
    ).all()

    if not course_sessions:
        default_session = CourseSession(
            course_id=course_id,
            topic=f"{course.code} - Session 1",
            date=datetime.utcnow().date()
        )
        db.session.add(default_session)
        db.session.commit()
        course_sessions = [default_session]

    session_ids = [s.id for s in course_sessions]
    active_session = None
    if session_ids:
        active_session = LectureSession.query.filter(
            LectureSession.course_session_id.in_(session_ids),
            LectureSession.active.is_(True),
        ).first()

    active_course_session_id = active_session.course_session_id if active_session else None

    if session_ids:
        past_sessions = LectureSession.query.filter(
            LectureSession.active == False,
            LectureSession.course_session_id.in_(session_ids),
        ).order_by(LectureSession.started_at.desc()).limit(20).all()
    else:
        past_sessions = []

    needs_attention = needs_attention_for_course(course_id)

    return render_template('class_rep_course_detail.html',
                            course=course,
                            course_sessions=course_sessions,
                            active_session=active_session,
                            active_course_session_id=active_course_session_id,
                            past_sessions=past_sessions,
                            needs_attention=needs_attention,
                            radius_metres=Config.GPS_BASE_RADIUS_METRES,
                            rep_accuracy_warn=Config.GPS_REP_ACCURACY_WARN_METRES,
                            rectify_ttl=Config.RECTIFY_TOKEN_TTL_SECONDS)


@class_rep_bp.route('/course/<int:course_id>/create-session', methods=['POST'])
@login_required
def create_course_session(course_id):
    classrep = _require_approved_classrep()
    if not classrep:
        return redirect(url_for('student.dashboard'))

    course = Course.query.get_or_404(course_id)
    if course.programme_id != classrep.programme_id:
        flash('This course is not in your programme.', 'error')
        return redirect(url_for('class_rep.dashboard'))

    existing_count = CourseSession.query.filter_by(course_id=course_id).count()
    topic = request.form.get('topic', '').strip() or f"{course.code} - Session {existing_count + 1}"

    course_session = CourseSession(
        course_id=course_id,
        topic=topic,
        date=datetime.utcnow().date()
    )
    db.session.add(course_session)
    db.session.commit()

    flash(f'New session "{topic}" created. Click "Start" on it when the lecture begins.', 'success')
    return redirect(url_for('class_rep.course_detail', course_id=course_id))


@class_rep_bp.route('/course-session/<int:session_id>/start', methods=['POST'])
@login_required
def start_session(session_id):
    classrep = _require_approved_classrep()
    if not classrep:
        return redirect(url_for('student.dashboard'))

    course_session = CourseSession.query.get_or_404(session_id)
    course_id = course_session.course_id

    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    accuracy = request.form.get('accuracy')
    if not lat or not lon:
        flash('Could not get your location. Please allow location access.', 'error')
        return redirect(url_for('class_rep.course_detail', course_id=course_id))

    try:
        lat = float(lat)
        lon = float(lon)
        accuracy = float(accuracy) if accuracy else None
    except ValueError:
        flash('Invalid location data.', 'error')
        return redirect(url_for('class_rep.course_detail', course_id=course_id))

    lecture_session, error = start_gps_session(course_session, current_user, lat, lon, accuracy)
    if error:
        flash(error, 'warning')
        return redirect(url_for('class_rep.course_detail', course_id=course_id))

    flash('Lecture session started! Students nearby can now mark attendance.', 'success')
    return redirect(url_for('class_rep.course_detail', course_id=course_id))


@class_rep_bp.route('/session/<int:session_id>/end', methods=['POST'])
@login_required
def end_session(session_id):
    lecture_session = LectureSession.query.get_or_404(session_id)
    course = lecture_session.course_session.course

    if not can_manage_course(current_user, course):
        flash('You are not authorised to end this session.', 'error')
        return redirect(url_for('student.dashboard') if current_user.role == 'student' else url_for('lecturer.dashboard'))

    if not lecture_session.active:
        flash('This session is already ended.', 'warning')
        return redirect(url_for('class_rep.dashboard'))

    course_session = CourseSession.query.get(lecture_session.course_session_id)
    course_id = course_session.course_id if course_session else None

    close_gps_session(lecture_session)
    flash('Lecture session ended. Attendance has been recorded.', 'success')

    if current_user.role == 'lecturer':
        return redirect(url_for('lecturer.course_detail', course_id=course_id)) if course_id else redirect(url_for('lecturer.dashboard'))
    if course_id:
        return redirect(url_for('class_rep.course_detail', course_id=course_id))
    return redirect(url_for('class_rep.dashboard'))


@class_rep_bp.route('/session/<int:session_id>/attendance')
@login_required
def view_attendance(session_id):
    lecture_session = LectureSession.query.get_or_404(session_id)
    classrep = ClassRep.query.filter_by(user_id=current_user.id, approved=True).first()
    course = lecture_session.course_session.course
    if not (current_user.role == 'admin' or
            (current_user.role == 'lecturer' and course.lecturer_id == current_user.id) or
            (classrep and classrep.programme_id == course.programme_id)):
        flash('You are not authorised to view this attendance.', 'error')
        return redirect(url_for('class_rep.dashboard'))

    attendances = LectureAttendance.query.filter_by(
        lecture_session_id=session_id
    ).join(StudentProfile).join(User).order_by(User.full_name).all()

    present_count = LectureAttendance.query.filter_by(
        lecture_session_id=session_id, status='present'
    ).count()
    total_count = len(attendances)

    return render_template('attendance_print.html',
                            lecture_session=lecture_session,
                            attendances=attendances,
                            role='class_rep',
                            present_count=present_count,
                            total_count=total_count,
                            now=datetime.utcnow())


@class_rep_bp.route('/api/session/<int:session_id>/students')
@login_required
def api_session_students(session_id):
    lecture_session = LectureSession.query.get_or_404(session_id)
    course = lecture_session.course_session.course

    if not can_manage_course(current_user, course):
        return jsonify({'error': 'Unauthorized'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = LectureAttendance.query.filter_by(
        lecture_session_id=session_id
    ).join(StudentProfile).join(User)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    students = [{
        'name': att.student.user.full_name,
        'registration': att.student.registration_number,
        'status': att.status,
        'timestamp': att.timestamp.strftime('%H:%M') if att.timestamp else None
    } for att in paginated.items]

    return jsonify({
        'students': students,
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages
    })


@class_rep_bp.route('/rectify/<int:lecture_session_id>/<int:student_id>/generate', methods=['POST'])
@login_required
def generate_rectify(lecture_session_id, student_id):
    lecture_session = LectureSession.query.get_or_404(lecture_session_id)
    course = lecture_session.course_session.course

    if not can_manage_course(current_user, course):
        return jsonify({'error': 'You are not authorised to manage this course.'}), 403

    classrep = None
    if current_user.role == 'student':
        classrep = ClassRep.query.filter_by(user_id=current_user.id, approved=True).first()
        if not rep_has_checked_in(classrep, lecture_session):
            return jsonify({
                'error': 'Please mark your own attendance for this lecture before rectifying a student.'
            }), 400

    student = StudentProfile.query.get_or_404(student_id)

    already_marked = LectureAttendance.query.filter_by(
        lecture_session_id=lecture_session_id, student_id=student_id
    ).first()
    if already_marked:
        return jsonify({'error': 'This student is already marked present.'}), 400

    token = create_rectify_token(lecture_session, student, current_user, classrep=classrep)
    scan_url = url_for('student.rectify_scan', token=token.token, _external=True)

    return jsonify({
        'qr_data_url': generate_qr_data_url(scan_url),
        'expires_in_seconds': Config.RECTIFY_TOKEN_TTL_SECONDS,
        'student_name': student.user.full_name,
    })


@class_rep_bp.route('/course/<int:course_id>/needs-attention')
@login_required
def needs_attention_api(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(current_user, course):
        return jsonify({'error': 'Not authorised for this course'}), 403
    return jsonify({'students': needs_attention_for_course(course_id)})


@class_rep_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register_request():
    if current_user.role != 'student':
        flash('Only students can apply to be class representatives.', 'error')
        return redirect(url_for('student.dashboard'))

    existing_request = ClassRep.query.filter_by(user_id=current_user.id).first()

    if existing_request:
        if request.method == 'POST':
            flash('You have already submitted a request.', 'info')
            return redirect(url_for('class_rep.register_request'))
        return render_template('classrep_register.html',
                                programmes=Programme.query.all(),
                                existing_request=existing_request)

    if request.method == 'POST':
        programme_id = request.form.get('programme_id')
        if not programme_id:
            flash('Please select your programme.', 'error')
            return render_template('classrep_register.html',
                                    programmes=Programme.query.all(),
                                    existing_request=None)

        programme_id = int(programme_id)
        existing_count = ClassRep.query.filter_by(programme_id=programme_id).count()
        if existing_count >= Config.MAX_CLASS_REPS_PER_PROGRAMME:
            flash(f'This programme already has the maximum of {Config.MAX_CLASS_REPS_PER_PROGRAMME} class representatives. Contact admin if you believe this is a mistake.', 'error')
            return render_template('classrep_register.html',
                                    programmes=Programme.query.all(),
                                    existing_request=None)

        classrep = ClassRep(
            user_id=current_user.id,
            programme_id=programme_id,
            approved=False
        )
        db.session.add(classrep)
        db.session.commit()

        # PROFESSIONAL FIX: deduplicated admin alert instead of raw Notification loop
        notify_admins(
            message=f'New class rep request from {current_user.full_name} ({current_user.email})',
            link=url_for('admin.classrep_requests'),
            dedup_hours=1
        )

        flash('Your request has been submitted to the admin for approval.', 'success')
        return redirect(url_for('student.dashboard'))

    programmes = Programme.query.order_by(Programme.name).all()
    return render_template('classrep_register.html',
                            programmes=programmes,
                            existing_request=None)