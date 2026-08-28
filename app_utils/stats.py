from sqlalchemy import func

from extensions import db
from models import CourseSession, AttendanceRecord, StudentProfile, User, Enrollment


def course_attendance_for_student(course_id, student_id):
    total = CourseSession.query.filter_by(course_id=course_id).filter(
        CourseSession.closed_at.isnot(None)
    ).count()
    if total == 0:
        return 0, 0, 0.0
    present = AttendanceRecord.query.join(CourseSession).filter(
        CourseSession.course_id == course_id,
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.status.in_(["present", "late"]),
    ).count()
    pct = (present / total) * 100
    return present, total, pct


def course_roster_stats(course):
    total_sessions = CourseSession.query.filter_by(
        course_id=course.id
    ).filter(CourseSession.closed_at.isnot(None)).count()

    sessions = CourseSession.query.filter_by(
        course_id=course.id
    ).filter(CourseSession.closed_at.isnot(None)).order_by(
        CourseSession.date.desc()
    ).limit(5).all()[::-1]

    session_ids = [s.id for s in sessions]

    present_counts = dict(
        db.session.query(
            AttendanceRecord.student_id, func.count(AttendanceRecord.id)
        )
        .join(CourseSession, AttendanceRecord.session_id == CourseSession.id)
        .filter(
            CourseSession.course_id == course.id,
            CourseSession.closed_at.isnot(None),
            AttendanceRecord.status.in_(["present", "late"]),
        )
        .group_by(AttendanceRecord.student_id)
        .all()
    )

    history_map = {}
    if session_ids:
        records = AttendanceRecord.query.filter(
            AttendanceRecord.session_id.in_(session_ids),
            AttendanceRecord.status.in_(["present", "late"]),
        ).all()
        for r in records:
            if r.student_id not in history_map:
                history_map[r.student_id] = {}
            history_map[r.student_id][r.session_id] = 1

    enrolled = (
        db.session.query(StudentProfile, User)
        .join(User, StudentProfile.user_id == User.id)
        .join(Enrollment, Enrollment.student_id == StudentProfile.id)
        .filter(Enrollment.course_id == course.id)
        .all()
    )

    rows = []
    for student, user in enrolled:
        present = present_counts.get(student.id, 0)
        pct = (present / total_sessions * 100) if total_sessions else 0.0
        
        history = []
        for sid in session_ids:
            history.append(1 if (history_map.get(student.id) or {}).get(sid) else 0)
        
        rows.append({
            "student_id": student.id,
            "name": user.full_name,
            "student_number": student.student_number,
            "present": present,
            "total": total_sessions,
            "percentage": pct,
            "history": history,
        })
    rows.sort(key=lambda r: r["name"])
    return rows


def predict_at_risk_trend(history, threshold=75.0):
    """
    Simple linear regression on last N sessions (1=present, 0=absent).
    Returns (current_pct, projected_final_pct, is_trending_at_risk).
    """
    n = len(history)
    if n < 2:
        return 0.0, 0.0, False
    
    current_pct = (sum(history) / n) * 100
    
    # Linear regression: x = session index, y = cumulative average
    cum = []
    s = 0
    for i, h in enumerate(history):
        s += h
        cum.append((s / (i + 1)) * 100)
    
    x_mean = sum(range(n)) / n
    y_mean = sum(cum) / n
    
    num = sum((i - x_mean) * (cum[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    
    if den == 0:
        return current_pct, current_pct, False
    
    slope = num / den
    projected = cum[-1] + (slope * (n - 1))
    projected = max(0.0, min(100.0, projected))
    
    is_trending_at_risk = projected < threshold and current_pct >= threshold
    return current_pct, projected, is_trending_at_risk