import logging
from werkzeug.security import generate_password_hash
from extensions import db
from models import User, Course, ClassRep

logger = logging.getLogger(__name__)


def seed_database():
    """
    Populates the database with full course listings across all Makerere University colleges 
    and essential default accounts (Admin, Lecturers, Students) if they do not already exist.
    """
    try:
        # ---------------------------------------------------------
        # 1. Seed Courses Across All Colleges
        # ---------------------------------------------------------
        courses_data = [
            # COCIS - College of Computing & Information Sciences
            {"code": "CSC 1100", "name": "Computer Literacy", "department": "Computer Science", "college": "COCIS"},
            {"code": "CSC 1200", "name": "Structured Programming in C", "department": "Computer Science", "college": "COCIS"},
            {"code": "CSC 2100", "name": "Data Structures & Algorithms", "department": "Computer Science", "college": "COCIS"},
            {"code": "CSC 3101", "name": "Computer Organization & Architecture", "department": "Computer Science", "college": "COCIS"},
            {"code": "CSC 3205", "name": "Artificial Intelligence & Machine Learning", "department": "Computer Science", "college": "COCIS"},
            {"code": "BSSE 1101", "name": "Introduction to Software Engineering", "department": "Software Engineering", "college": "COCIS"},
            {"code": "BSSE 2201", "name": "Software Architecture & Design Patterns", "department": "Software Engineering", "college": "COCIS"},
            {"code": "BIT 2103", "name": "Database Systems & Administration", "department": "Information Technology", "college": "COCIS"},
            {"code": "BIT 3104", "name": "Web Application Development", "department": "Information Technology", "college": "COCIS"},

            # CEDAT - College of Engineering, Design, Art and Technology
            {"code": "ELE 1101", "name": "Introduction to Electrical Engineering", "department": "Electrical Engineering", "college": "CEDAT"},
            {"code": "ELE 2203", "name": "Signals and Systems", "department": "Electrical Engineering", "college": "CEDAT"},
            {"code": "CIV 2102", "name": "Fluid Mechanics for Civil Engineers", "department": "Civil Engineering", "college": "CEDAT"},
            {"code": "CIV 3105", "name": "Structural Analysis", "department": "Civil Engineering", "college": "CEDAT"},
            {"code": "MEC 3103", "name": "Applied Thermodynamics", "department": "Mechanical Engineering", "college": "CEDAT"},

            # CONAS - College of Natural Sciences
            {"code": "MTH 1101", "name": "Calculus I", "department": "Mathematics", "college": "CONAS"},
            {"code": "MTH 1201", "name": "Linear Algebra", "department": "Mathematics", "college": "CONAS"},
            {"code": "PHY 1102", "name": "General University Physics", "department": "Physics", "college": "CONAS"},
            {"code": "CHM 1101", "name": "Physical Chemistry", "department": "Chemistry", "college": "CONAS"},

            # COBAMS - College of Business and Management Sciences
            {"code": "ECO 1101", "name": "Principles of Microeconomics", "department": "Economics", "college": "COBAMS"},
            {"code": "ECO 1201", "name": "Principles of Macroeconomics", "department": "Economics", "college": "COBAMS"},
            {"code": "ACC 1200", "name": "Financial Accounting I", "department": "Accounting", "college": "COBAMS"},
            {"code": "FIN 2101", "name": "Corporate Finance", "department": "Finance", "college": "COBAMS"},
            {"code": "BBA 2204", "name": "Principles of Marketing", "department": "Business Administration", "college": "COBAMS"},

            # CHUSS - College of Humanities and Social Sciences
            {"code": "SOC 1101", "name": "Introduction to Sociology", "department": "Sociology", "college": "CHUSS"},
            {"code": "POS 1201", "name": "Political Ideas and Governance", "department": "Political Science", "college": "CHUSS"},
            {"code": "LIT 2101", "name": "African Literature", "department": "Literature", "college": "CHUSS"},

            # CHS - College of Health Sciences
            {"code": "ANAT 1101", "name": "Human Anatomy I", "department": "Human Anatomy", "college": "CHS"},
            {"code": "PHAR 2103", "name": "Pharmacology and Therapeutics", "department": "Pharmacy", "college": "CHS"}
        ]

        seeded_courses_count = 0
        for info in courses_data:
            # Check for existing course by code if field exists
            existing = None
            if hasattr(Course, 'code'):
                existing = Course.query.filter_by(code=info["code"]).first()
            elif hasattr(Course, 'course_code'):
                existing = Course.query.filter_by(course_code=info["code"]).first()

            if not existing:
                c = Course()
                # Dynamically set attribute depending on model property names
                if hasattr(c, 'code'):
                    c.code = info["code"]
                elif hasattr(c, 'course_code'):
                    c.course_code = info["code"]

                if hasattr(c, 'name'):
                    c.name = info["name"]
                elif hasattr(c, 'title'):
                    c.title = info["name"]

                if hasattr(c, 'department'):
                    c.department = info["department"]

                if hasattr(c, 'college'):
                    c.college = info["college"]

                db.session.add(c)
                seeded_courses_count += 1

        db.session.commit()
        logger.info(f"[Database Seed] Seeded {seeded_courses_count} new courses across Mak colleges.")

        # ---------------------------------------------------------
        # 2. Seed System Administrative & Default Users
        # ---------------------------------------------------------
        default_users = [
            {
                "email": "admin@mak.ac.ug",
                "name": "System Administrator",
                "role": "admin",
                "program": "Administrator"
            },
            {
                "email": "lecturer@mak.ac.ug",
                "name": "Dr. Joseph Okello",
                "role": "lecturer",
                "program": "Computer Science"
            },
            {
                "email": "student@mak.ac.ug",
                "name": "Muwanguzi Joshua",
                "role": "student",
                "program": "Computer Science",
                "is_class_rep": True
            }
        ]

        for u_data in default_users:
            if hasattr(User, 'email'):
                existing_user = User.query.filter_by(email=u_data["email"]).first()
                if not existing_user:
                    u = User()
                    u.email = u_data["email"]
                    if hasattr(u, 'name'):
                        u.name = u_data["name"]
                    elif hasattr(u, 'username'):
                        u.username = u_data["name"]

                    if hasattr(u, 'role'):
                        u.role = u_data["role"]
                    if hasattr(u, 'program'):
                        u.program = u_data["program"]
                    if hasattr(u, 'is_class_rep') and 'is_class_rep' in u_data:
                        u.is_class_rep = u_data["is_class_rep"]

                    # Set password hash if method or field exists
                    if hasattr(u, 'set_password'):
                        u.set_password("Password123!")
                    elif hasattr(u, 'password_hash'):
                        u.password_hash = generate_password_hash("Password123!")
                    elif hasattr(u, 'password'):
                        u.password = generate_password_hash("Password123!")

                    db.session.add(u)

        db.session.commit()
        logger.info("[Database Seed] Default users checked and created successfully.")

    except Exception as e:
        db.session.rollback()
        logger.error(f"[Database Seed] Error seeding database: {e}")
        raise e