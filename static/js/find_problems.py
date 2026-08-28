import os

print("=" * 60)
print("SCANNING FOR COMMON ISSUES")
print("=" * 60)

# 1. Check for remaining 'from utils.' imports
print("\n[1] Checking for remaining 'from utils.' imports...")
bad_imports = []
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if "from utils." in line or ("import utils" in line and "app_utils" not in line):
                    bad_imports.append((path, i, line.strip()))

if bad_imports:
    print(f"   FOUND {len(bad_imports)} bad imports:")
    for path, line_no, line in bad_imports:
        print(f"   - {path}:{line_no} -> {line}")
else:
    print("   All imports look good!")

# 2. Check if app_utils files exist
print("\n[2] Checking app_utils folder...")
app_utils_files = ["__init__.py", "notifications.py", "audit.py", "session_control.py"]
for f in app_utils_files:
    path = os.path.join("app_utils", f)
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"   OK: app_utils/{f} ({size} bytes)")
    else:
        print(f"   MISSING: app_utils/{f}")

# 3. Check for JSON files
print("\n[3] Checking JSON files...")
import json
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".json"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
                print(f"   OK: {path}")
            except json.JSONDecodeError as e:
                print(f"   BROKEN: {path} -> {e}")

# 4. Check database tables
print("\n[4] Checking database (if SQLite)...")
db_path = "instance/app.db"
if not os.path.exists(db_path):
    db_path = "app.db"
if os.path.exists(db_path):
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"   Database found: {db_path}")
        print(f"   Tables: {', '.join(tables)}")
        
        required = ["audit_log", "lecturer_activation_code", "notification"]
        missing = [t for t in required if t not in tables]
        if missing:
            print(f"   MISSING TABLES: {', '.join(missing)} -> Run: flask db upgrade")
        else:
            print("   All required tables present.")
    except Exception as e:
        print(f"   Could not read database: {e}")
else:
    print(f"   No SQLite database found at {db_path}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)