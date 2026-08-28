"""
app/utils/checkin_queue.py

Queuing logic for students who need attention during a live session.
Tracks failed check-in attempts and generates rectify tokens for manual assistance.
"""

from datetime import datetime, timedelta
import secrets

from extensions import db
from models import CheckInAttempt, RectifyToken, StudentProfile, LectureSession, CourseSession, Course
from config import Config


def log_attempt(lecture_session, profile, success, failure_reason=None, method="auto"):
    """
    Log a check-in attempt for a student in a lecture session.
    """
    if not lecture_session or not profile:
        return None
    
    # Count existing attempts for this student in this session
    existing_count = CheckInAttempt.query.filter_by(
        lecture_session_id=lecture_session.id,
        student_id=profile.id
    ).count()
    
    attempt = CheckInAttempt(
        lecture_session_id=lecture_session.id,
        student_id=profile.id,
        attempt_number=existing_count + 1,
        method=method,
        success=success,
        failure_reason=failure_reason
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def needs_attention_for_course(course_id):
    """
    Returns list of students who need attention for a specific course.
    A student needs attention if they have failed check-in attempts
    without a success yet.
    """
    # Get all active lecture sessions for this course
    lecture_sessions = LectureSession.query.join(
        CourseSession, LectureSession.course_session_id == CourseSession.id
    ).filter(
        CourseSession.course_id == course_id,
        LectureSession.active == True
    ).all()
    
    if not lecture_sessions:
        return []
    
    session_ids = [s.id for s in lecture_sessions]
    
    # Get students who have failed attempts but no success for this session
    result = []
    for session in lecture_sessions:
        # Get failed attempts for this session
        failed_attempts = CheckInAttempt.query.filter(
            CheckInAttempt.lecture_session_id == session.id,
            CheckInAttempt.success == False
        ).all()
        
        # Get successful attempts for this session
        success_students = set(
            a.student_id for a in CheckInAttempt.query.filter(
                CheckInAttempt.lecture_session_id == session.id,
                CheckInAttempt.success == True
            ).all()
        )
        
        # Group failed attempts by student
        student_failures = {}
        for attempt in failed_attempts:
            if attempt.student_id not in student_failures:
                student_failures[attempt.student_id] = []
            student_failures[attempt.student_id].append(attempt)
        
        # Only include students who have failed but not succeeded
        for student_id, attempts in student_failures.items():
            if student_id not in success_students:
                profile = StudentProfile.query.get(student_id)
                if profile and profile.user:
                    result.append({
                        'student_id': student_id,
                        'student_name': profile.user.full_name,
                        'failed_attempts': len(attempts),
                        'lecture_session_id': session.id,
                        'last_reason': attempts[-1].failure_reason if attempts else None
                    })
    
    return result


def needs_attention_for_programme(programme_id):
    """
    Returns list of students who need attention for a specific programme.
    """
    # Get all courses in this programme
    courses = Course.query.filter_by(programme_id=programme_id).all()
    course_ids = [c.id for c in courses]
    
    if not course_ids:
        return [], 0
    
    # Get all active lecture sessions for these courses
    lecture_sessions = LectureSession.query.join(
        CourseSession, LectureSession.course_session_id == CourseSession.id
    ).filter(
        CourseSession.course_id.in_(course_ids),
        LectureSession.active == True
    ).all()
    
    if not lecture_sessions:
        return [], 0
    
    all_attention = []
    for session in lecture_sessions:
        attention_list = needs_attention_for_course(session.course_session.course_id)
        all_attention.extend(attention_list)
    
    # Remove duplicates by student_id
    seen = set()
    unique_attention = []
    for item in all_attention:
        if item['student_id'] not in seen:
            seen.add(item['student_id'])
            unique_attention.append(item)
    
    return unique_attention, len(unique_attention)


def get_valid_token(token_str):
    """
    Get a valid rectify token if it exists and hasn't expired/been used.
    """
    if not token_str:
        return None
    
    token = RectifyToken.query.filter_by(token=token_str).first()
    if not token:
        return None
    
    if token.is_expired or token.is_used:
        return None
    
    return token


def create_rectify_token(lecture_session, student, issued_by, classrep=None):
    """
    Create a new rectify token for a student.
    """
    # Invalidate any existing unused tokens for this student and session
    existing = RectifyToken.query.filter_by(
        lecture_session_id=lecture_session.id,
        student_id=student.id,
        used_at=None
    ).all()
    
    for token in existing:
        token.used_at = datetime.utcnow()  # Mark as used to invalidate
    
    # Create new token
    token = RectifyToken(
        lecture_session_id=lecture_session.id,
        student_id=student.id,
        class_rep_id=classrep.id if classrep else None,
        issued_by_user_id=issued_by.id,
        expires_at=datetime.utcnow() + timedelta(seconds=Config.RECTIFY_TOKEN_TTL_SECONDS)
    )
    db.session.add(token)
    db.session.commit()
    
    return token