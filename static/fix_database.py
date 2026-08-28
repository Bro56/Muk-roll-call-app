"""
fix_database.py
Auto-detects and fixes missing tables/columns by comparing models.py to your PostgreSQL database.
"""
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError
from app import create_app
from extensions import db
from models import (
    User, StudentProfile, LecturerProfile, AdminProfile,
    College, School, Department, Programme, Course, CourseSession,
    LectureSession, CheckInAttempt, ClassRep, Notification,
    LecturerActivationCode, AuditLog
)

app = create_app()
app.app_context().push()

engine = db.engine
insp = inspect(engine)

# All models to check
MODELS = [
    User, StudentProfile, LecturerProfile, AdminProfile,
    College, School, Department, Programme, Course, CourseSession,
    LectureSession, CheckInAttempt, ClassRep, Notification,
    LecturerActivationCode, AuditLog
]

print("=" * 60)
print("DATABASE SCHEMA FIXER")
print("=" * 60)

# 1. Check for missing tables
print("\n[1] Checking for missing tables...")
missing_tables = []
for model in MODELS:
    table_name = model.__tablename__
    if not insp.has_table(table_name):
        missing_tables.append(table_name)
        print(f"   MISSING TABLE: {table_name}")
    else:
        print(f"   OK: {table_name}")

# 2. Create missing tables
if missing_tables:
    print(f"\n[2] Creating {len(missing_tables)} missing tables...")
    db.create_all()
    print("   Done! Tables created.")
else:
    print("\n[2] All tables exist.")

# 3. Check for missing columns
print("\n[3] Checking for missing columns...")
fix_sql = []

for model in MODELS:
    table_name = model.__tablename__
    if not insp.has_table(table_name):
        continue
    
    existing_cols = {c['name'] for c in insp.get_columns(table_name)}
    mapper = inspect(model)
    
    for col in mapper.columns:
        if col.name not in existing_cols:
            col_type = col.type.compile(dialect=engine.dialect)
            nullable = "NULL" if col.nullable else "NOT NULL"
            default = ""
            
            if col.default is not None and hasattr(col.default, 'arg'):
                default_val = col.default.arg
                if isinstance(default_val, bool):
                    default = f" DEFAULT {'TRUE' if default_val else 'FALSE'}"
                elif isinstance(default_val, str):
                    default = f" DEFAULT '{default_val}'"
                else:
                    default = f" DEFAULT {default_val}"
            
            sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col.name} {col_type} {nullable}{default};"
            fix_sql.append(sql)
            print(f"   MISSING: {table_name}.{col.name} ({col_type})")

# 4. Execute fixes
if fix_sql:
    print(f"\n[4] Adding {len(fix_sql)} missing columns...")
    with engine.connect() as conn:
        for sql in fix_sql:
            try:
                conn.execute(text(sql))
                print(f"   FIXED: {sql[:60]}...")
            except Exception as e:
                print(f"   ERROR: {sql[:60]}... -> {e}")
        conn.commit()
    print("   Done! All columns added.")
else:
    print("\n[4] All columns exist. No fixes needed.")

# 5. Verify indexes
print("\n[5] Checking indexes...")
for model in MODELS:
    table_name = model.__tablename__
    if not insp.has_table(table_name):
        continue
    try:
        existing_indexes = {idx['name'] for idx in insp.get_indexes(table_name)}
        for idx in model.__table__.indexes:
            if idx.name not in existing_indexes:
                print(f"   MISSING INDEX: {idx.name} on {table_name}")
                # Create index
                idx.create(engine)
                print(f"   CREATED: {idx.name}")
    except Exception as e:
        print(f"   SKIP: {table_name} indexes -> {e}")

print("\n" + "=" * 60)
print("DATABASE FIX COMPLETE")
print("=" * 60)
print("\nRestart your Flask app: python app.py")