"""
fix_database.py
Universal database fixer. Works with ANY model names in your models.py.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

app = create_app()
app.app_context().push()

engine = db.engine
insp = inspect(engine)

print("=" * 60)
print("DATABASE SCHEMA FIXER")
print(f"Database: {engine.url}")
print("=" * 60)

# Get all tables from SQLAlchemy metadata (reads your models.py automatically)
all_tables = db.metadata.sorted_tables
print(f"\nFound {len(all_tables)} tables defined in models.py:")
for table in all_tables:
    print(f"   - {table.name}")

# 1. Create missing tables
print("\n[1] Creating missing tables...")
db.create_all()
print("   Done. All tables created/verified.")

# 2. Check and fix missing columns
print("\n[2] Checking for missing columns...")
fix_count = 0

for table in all_tables:
    table_name = table.name

    if not insp.has_table(table_name):
        print(f"   TABLE STILL MISSING: {table_name} (will be fixed by db.create_all())")
        continue

    # Get existing columns
    try:
        existing_cols = {c['name'] for c in insp.get_columns(table_name)}
    except Exception as e:
        print(f"   SKIP: Could not read columns for {table_name}: {e}")
        continue

    # Check each column defined in the model
    for column in table.columns:
        if column.name not in existing_cols:
            col_type = column.type.compile(dialect=engine.dialect)
            nullable = "NULL" if column.nullable else "NOT NULL"

            # Handle default values
            default_clause = ""
            if column.default is not None:
                if hasattr(column.default, 'arg'):
                    arg = column.default.arg
                    if isinstance(arg, bool):
                        default_clause = f" DEFAULT {'TRUE' if arg else 'FALSE'}"
                    elif isinstance(arg, str):
                        default_clause = f" DEFAULT '{arg}'"
                    elif isinstance(arg, (int, float)):
                        default_clause = f" DEFAULT {arg}"

            sql = f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{column.name}" {col_type} {nullable}{default_clause};'

            try:
                with engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                print(f"   FIXED: {table_name}.{column.name} ({col_type})")
                fix_count += 1
            except Exception as e:
                print(f"   ERROR adding {table_name}.{column.name}: {e}")
                print(f"   SQL attempted: {sql}")

if fix_count == 0:
    print("   All columns already exist. No fixes needed.")
else:
    print(f"\n   Total columns added: {fix_count}")

# 3. Verify everything
print("\n[3] Verification...")
for table in all_tables:
    table_name = table.name
    if insp.has_table(table_name):
        cols = [c['name'] for c in insp.get_columns(table_name)]
        missing = [c.name for c in table.columns if c.name not in cols]
        if missing:
            print(f"   STILL MISSING: {table_name} -> {', '.join(missing)}")
        else:
            print(f"   OK: {table_name} ({len(cols)} columns)")
    else:
        print(f"   FAIL: {table_name} does not exist!")

print("\n" + "=" * 60)
print("DATABASE FIX COMPLETE")
print("=" * 60)
print("\nRestart your Flask app: python app.py")