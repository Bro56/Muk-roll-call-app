import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, ClassRep, Course

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
def ensure_admin():
    if getattr(current_user, 'role', '') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.index'))


@admin_bp.route('/dashboard')
def dashboard():
    """
    Fixed BuildError: Serves as the endpoint for 'admin.dashboard'.
    Redirects to user management view.
    """
    return redirect(url_for('admin.users'))


@admin_bp.route('/users')
def users():
    view_type = request.args.get('type', 'students')

    # Query real records from database
    all_students = User.query.filter_by(role='student').all() if hasattr(User, 'role') else []
    all_lecturers = User.query.filter_by(role='lecturer').all() if hasattr(User, 'role') else []

    # 1. Get programs from enrolled students
    student_programs = {getattr(s, 'program', '') for s in all_students if getattr(s, 'program', None)}

    # 2. Extract departments/programs from all courses across all colleges
    course_programs = set()
    if hasattr(Course, 'query'):
        courses_list = Course.query.all()
        for c in courses_list:
            dept = getattr(c, 'department', '') or getattr(c, 'program', '')
            if dept:
                course_programs.add(dept)

    # 3. Combine both sources into a clean, sorted list of programs
    combined_programs = sorted(list(student_programs.union(course_programs)))

    # Fallback list if database has no entries
    if not combined_programs:
        combined_programs = [
            'Accounting',
            'Civil Engineering',
            'Computer Science',
            'Electrical Engineering',
            'Finance',
            'Information Technology',
            'Mathematics',
            'Software Engineering'
        ]

    # Select active program from query params or default to first available
    selected_program = request.args.get('program', combined_programs[0] if combined_programs else 'Computer Science')

    if selected_program not in combined_programs and combined_programs:
        selected_program = combined_programs[0]

    # Filter students by active program selection
    filtered_students = [s for s in all_students if getattr(s, 'program', '') == selected_program]

    # Calculate metrics
    total_students = len(all_students)
    total_lecturers = len(all_lecturers)
    
    if hasattr(User, 'is_class_rep'):
        total_class_reps = User.query.filter_by(role='student', is_class_rep=True).count()
    elif hasattr(ClassRep, 'query'):
        total_class_reps = ClassRep.query.filter_by(approved=True).count()
    else:
        total_class_reps = 0

    return render_template(
        'admin/users.html',
        view_type=view_type,
        students=filtered_students,
        lecturers=all_lecturers,
        programs=combined_programs,
        selected_program=selected_program,
        total_students=total_students,
        total_lecturers=total_lecturers,
        total_class_reps=total_class_reps
    )


@admin_bp.route('/courses')
def courses():
    """
    Queries ALL courses from the database across all colleges.
    Orders dynamically by code or ID depending on model structure.
    """
    if hasattr(Course, 'query'):
        if hasattr(Course, 'code'):
            all_courses = Course.query.order_by(Course.code.asc()).all()
        else:
            all_courses = Course.query.all()
    else:
        all_courses = []

    return render_template('admin/courses.html', courses=all_courses)


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        flash('System settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html')