from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_

from extensions import db
from models import User, Course, Programme, College, Department, School, Enrollment, StudentProfile

search_bp = Blueprint("search", __name__, url_prefix="/api/search")


def _rate_limit_decorator(limit_string):
    """Apply Flask-Limiter only if it is installed and initialized."""
    from extensions import limiter
    if limiter:
        return limiter.limit(limit_string)
    # No-op decorator
    def noop(f):
        return f
    return noop


@search_bp.route("")
@login_required
@_rate_limit_decorator("30 per minute")
def global_search():
    """
    Universal search API.
    Returns scoped results based on the current user's role.
    """
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"results": [], "query": q})

    like_pattern = f"%{q}%"
    results = []

    # ------------------------------------------------------------------
    # ADMIN: users, courses, programmes, colleges, departments, schools
    # ------------------------------------------------------------------
    if current_user.role == "admin":
        users = User.query.filter(
            or_(
                User.full_name.ilike(like_pattern),
                User.username.ilike(like_pattern),
                User.email.ilike(like_pattern),
            )
        ).order_by(User.full_name).limit(5).all()

        courses = Course.query.join(Programme).filter(
            or_(
                Course.name.ilike(like_pattern),
                Course.code.ilike(like_pattern),
            )
        ).order_by(Course.code).limit(5).all()

        programmes = Programme.query.filter(
            or_(
                Programme.name.ilike(like_pattern),
                Programme.code.ilike(like_pattern),
            )
        ).order_by(Programme.name).limit(5).all()

        colleges = College.query.filter(
            College.name.ilike(like_pattern)
        ).order_by(College.name).limit(3).all()

        departments = Department.query.filter(
            Department.name.ilike(like_pattern)
        ).order_by(Department.name).limit(3).all()

        results = [
            *[_user_result(u) for u in users],
            *[_course_result(c, admin=True) for c in courses],
            *[_programme_result(p) for p in programmes],
            *[_college_result(c) for c in colleges],
            *[_department_result(d) for d in departments],
        ]

    # ------------------------------------------------------------------
    # LECTURER: only their own courses + enrolled students in those courses
    # ------------------------------------------------------------------
    elif current_user.role == "lecturer":
        courses = Course.query.filter(
            Course.lecturer_id == current_user.id,
            or_(
                Course.name.ilike(like_pattern),
                Course.code.ilike(like_pattern),
            )
        ).order_by(Course.code).limit(10).all()

        results = [
            *[_course_result(c, admin=False) for c in courses],
        ]

    # ------------------------------------------------------------------
    # STUDENT / CLASS REP: enrolled courses + all available courses
    # ------------------------------------------------------------------
    elif current_user.role in ("student", "class_rep"):
        profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
        enrolled_ids = []
        if profile:
            enrolled_ids = [
                e.course_id for e in
                Enrollment.query.filter_by(student_id=profile.id).all()
            ]

        courses = Course.query.filter(
            or_(
                Course.name.ilike(like_pattern),
                Course.code.ilike(like_pattern),
            )
        ).order_by(Course.code).limit(10).all()

        for c in courses:
            is_enrolled = c.id in enrolled_ids
            results.append({
                "type": "course",
                "title": c.code,
                "subtitle": f"{c.name} · {'Enrolled' if is_enrolled else 'Available'}",
                "url": url_for("student.course_detail", course_id=c.id) if is_enrolled else url_for("student.choose_courses"),
                "icon": "book",
                "meta": {"enrolled": is_enrolled}
            })

    return jsonify({"results": results, "query": q})


# ------------------------------------------------------------------
# Result builders (keep JSON shape consistent)
# ------------------------------------------------------------------

def _user_result(u):
    role_label = u.role.replace("_", " ").title()
    return {
        "type": "user",
        "title": u.full_name,
        "subtitle": f"@{u.username} · {role_label}",
        "url": url_for("admin.users"),
        "icon": "user",
    }


def _course_result(c, admin=False):
    return {
        "type": "course",
        "title": c.code,
        "subtitle": c.name,
        "url": url_for("admin.courses") if admin else url_for("lecturer.course_detail", course_id=c.id),
        "icon": "book",
    }


def _programme_result(p):
    return {
        "type": "programme",
        "title": p.name,
        "subtitle": p.code or "",
        "url": url_for("admin.structure"),
        "icon": "graduation-cap",
    }


def _college_result(c):
    return {
        "type": "college",
        "title": c.name,
        "subtitle": c.code,
        "url": url_for("admin.structure"),
        "icon": "building",
    }


def _department_result(d):
    return {
        "type": "department",
        "title": d.name,
        "subtitle": d.school.name if d.school else "",
        "url": url_for("admin.structure"),
        "icon": "building",
    }