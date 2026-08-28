# routes/__init__.py
# This file only imports and exposes blueprints.
# All database models are defined in models/__init__.py

from routes.auth import auth_bp
from routes.student import student_bp
from routes.lecturer import lecturer_bp
from routes.admin import admin_bp
from routes.class_rep import class_rep_bp