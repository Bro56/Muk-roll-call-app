from datetime import datetime
from typing import Tuple, Optional

from extensions import db, socketio
from models import LectureSession, LectureAttendance, AttendanceRecord, StudentProfile, CourseSession


def record_gps_attendance(
    lecture_session: LectureSession,
    profile: StudentProfile,
    status: str = "present",
    gps_accuracy: Optional[float] = None,
    face_verified: bool = True,
) -> Tuple[bool, str]:
    try:
        existing_lecture = LectureAttendance.query.filter_by(
            lecture_session_id=lecture_session.id,
            student_id=profile.id
        ).first()
        
        if not existing_lecture:
            lecture_att = LectureAttendance(
                lecture_session_id=lecture_session.id,
                student_id=profile.id,
                status=status,
                gps_accuracy=gps_accuracy,
                face_verified=face_verified
            )
            db.session.add(lecture_att)
        
        course_session_id = lecture_session.course_session_id
        existing_record = AttendanceRecord.query.filter_by(
            session_id=course_session_id,
            student_id=profile.id
        ).first()
        
        if not existing_record:
            record = AttendanceRecord(
                session_id=course_session_id,
                student_id=profile.id,
                status=status,
                method="face" if face_verified else "manual",
                marked_at=datetime.utcnow()
            )
            db.session.add(record)
        
        db.session.commit()
        
        socketio.emit('student_checked_in', {
            'course_id': lecture_session.course_session.course_id,
            'session_id': lecture_session.id,
            'student_name': profile.user.full_name,
            'student_id': profile.id,
            'checked_in_count': len(lecture_session.attendances),
            'total_enrolled': len(lecture_session.course_session.course.enrollments),
        }, room=f"course_{lecture_session.course_session.course_id}")
        
        return True, "Attendance recorded successfully."
        
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to record attendance: {str(e)}"


def close_gps_session(lecture_session: LectureSession) -> Tuple[bool, str]:
    if not lecture_session:
        return False, "Session not found."

    try:
        course_session = CourseSession.query.get(lecture_session.course_session_id)
        
        lecture_session.active = False
        lecture_session.ended_at = datetime.utcnow()
        
        if course_session:
            course_session.closed_at = datetime.utcnow()
        
        from models import Enrollment
        enrollments = Enrollment.query.filter_by(course_id=course_session.course_id).all()
        
        for enrollment in enrollments:
            existing = LectureAttendance.query.filter_by(
                lecture_session_id=lecture_session.id,
                student_id=enrollment.student_id
            ).first()
            
            if not existing:
                att = LectureAttendance(
                    lecture_session_id=lecture_session.id,
                    student_id=enrollment.student_id,
                    status="absent"
                )
                db.session.add(att)
            
            existing_record = AttendanceRecord.query.filter_by(
                session_id=course_session.id,
                student_id=enrollment.student_id
            ).first()
            
            if not existing_record:
                record = AttendanceRecord(
                    session_id=course_session.id,
                    student_id=enrollment.student_id,
                    status="absent",
                    method="auto"
                )
                db.session.add(record)
        
        db.session.commit()
        
        socketio.emit('session_ended', {
            'course_id': course_session.course_id,
            'session_id': lecture_session.id,
        }, room=f"course_{course_session.course_id}")
        
        return True, f"Session {lecture_session.id} successfully closed."
        
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to close session: {str(e)}"