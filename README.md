# Makerere University Roll Call

A biometric attendance system built for Makerere University's real academic
structure (College → School → Department → Programme → Course). Students
enroll their face once at signup; lecturers run live camera roll call that
recognizes and checks students in automatically, with a QR-code fallback and
manual override always available.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.x-black)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- **Real biometric face recognition** — via the [`face_recognition`](https://github.com/ageitgey/face_recognition) library (dlib-based), not a gimmick. A student's enrollment photo is converted into a 128-dimension face signature; live roll call compares camera frames against every enrolled student in that course.
- **Full Makerere academic hierarchy** — College → School → Department → Programme → Course, seeded with the real structure of all 9 colleges + the School of Law + MUBS.
- **Student self-service** — sign up, capture your face, pick your college/school/department/programme, add your courses, and track your attendance % per course and overall.
- **Attendance eligibility alerts** — courses below the configurable threshold (default 75%, Makerere's standard) are flagged "at risk" for both students and lecturers.
- **QR-code backup check-in** — if the camera isn't available, students scan a per-session QR code (or type its code) to self check-in.
- **Lecturer tools** — live roll call view, manual present/absent override, CSV and PDF attendance export per course.
- **Admin panel** — manage colleges/schools/departments/programmes/courses, assign lecturers, manage user accounts.
- **Modern, animated UI** — light/dark themes, an original animated crest (torch + open book, inspired by Makerere's "We Build For The Future" motto), smooth transitions, live scan effects, confetti on successful check-in.

---

## 🏗 Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3 + Flask |
| Database | SQLite via SQLAlchemy (zero-config, file-based) |
| Auth | Flask-Login (session-based) |
| Biometrics | `face_recognition` (dlib) |
| QR codes | `qrcode` |
| PDF export | `reportlab` |
| Frontend | Server-rendered Jinja templates + vanilla JS (no build step) |

---

## 🚀 Quick start

### Windows (recommended path)

1. Install [Python 3.10 or 3.11](https://www.python.org/downloads/) — **tick "Add Python to PATH"** during install.
2. Double-click **`run_app.bat`**.
3. The script creates a virtual environment, installs everything, and opens your browser to `http://127.0.0.1:5000` automatically.
4. Log in as admin with `admin` / `admin123` (change this immediately — see [Security notes](#-security-notes)).

### macOS / Linux

```bash
./run_app.sh
```

### Manual setup (any OS)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

---

## ⚠️ Troubleshooting: installing `face_recognition` / `dlib` on Windows

This is the one genuinely fiddly part of the setup, because `dlib` compiles
from C++ source. If `run_app.bat` fails at the `pip install -r requirements.txt`
step, try one of these:

**Option A — Use conda (easiest)**
```bash
conda create -n rollcall python=3.10
conda activate rollcall
conda install -c conda-forge dlib
pip install -r requirements.txt
```

**Option B — Install build tools, then pip**
1. Install [CMake](https://cmake.org/download/) and add it to PATH.
2. Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the "Desktop development with C++" workload.
3. Re-run `run_app.bat`.

**Option C — Precompiled wheel**
Search for a prebuilt `dlib` wheel matching your Python version (e.g. via
`pipwin install dlib`), install it first, then `pip install -r requirements.txt`.

If biometrics still won't install, the rest of the app (QR check-in, manual
marking, dashboards, admin panel) works completely fine without it — you can
run it and add biometrics later.

---

## 📂 Project structure

```
makerere-rollcall/
├── app.py                    # Flask app factory + entrypoint
├── config.py                 # App configuration (thresholds, paths)
├── extensions.py             # SQLAlchemy / Flask-Login singletons
├── requirements.txt
├── run_app.bat                # Windows one-click setup + launch
├── run_app.sh                 # macOS/Linux equivalent
├── models/
│   └── __init__.py           # All database models
├── database/
│   ├── seed_data.py          # Real Makerere college/school/dept/programme/course data
│   └── seed.py                # Loads seed data + creates default admin
├── routes/
│   ├── auth.py                # Login, signup, theme toggle, cascading dropdown APIs
│   ├── student.py             # Dashboard, course enrollment, QR check-in
│   ├── lecturer.py            # Roster, live roll call, biometric scan API, exports
│   └── admin.py                # Academic structure CRUD, course/lecturer assignment, users
├── utils/
│   ├── face_utils.py          # face_recognition wrappers (encode, match)
│   ├── qr_utils.py             # QR code generation
│   ├── report_utils.py        # CSV/PDF export builders
│   └── stats.py                # Attendance percentage calculations
├── templates/                 # Jinja2 HTML templates
├── static/
│   ├── css/style.css          # Design system (light/dark themes, animations)
│   ├── js/                     # Webcam capture, theme toggle, confetti
│   └── uploads/faces/          # Reference photos (git-ignored)
└── instance/
    └── rollcall.db             # SQLite database (created on first run, git-ignored)
```

---

## 🔐 How biometric check-in works

1. **Enrollment (signup):** the student's browser captures one webcam photo. It's sent to the server, where `face_recognition` locates the face and extracts a 128-number "signature" (encoding). Only this signature is used for matching — the photo itself is kept only so lecturers/admins can visually confirm identity in the roster.
2. **Roll call:** the lecturer starts a session and opens the live camera view. Every ~2 seconds, a frame is sent to the server, which compares any detected face(s) against the encodings of everyone enrolled in that course, using a distance threshold (`FACE_MATCH_TOLERANCE` in `config.py`, default `0.5` — lower is stricter).
3. **On a match**, that student is instantly marked present, with a confidence score.
4. **No match / camera issues:** the QR fallback or manual marking always works, so biometrics is a convenience layer, not a hard blocker to attendance.

---

## 🎓 About the seeded academic data

The Makerere structure (colleges, schools, departments) is modeled on the
university's real organization. Each department includes one representative
programme with a handful of first-year/second-year courses so the app is
usable out of the box — this is a **starting dataset**, not the complete
official catalogue. Admins can add more schools, departments, programmes,
and courses at any time from **Admin → Academic Structure** and
**Admin → Courses**.

---

## 🔒 Security notes

- Change the default admin password (`admin` / `admin123`) immediately after first login — via re-registering or updating it directly in the database for now (a password-change UI is a good next addition).
- This project is set up for local/campus deployment (e.g. a lecturer's laptop connected to a projector). If you deploy it publicly, put it behind HTTPS, change `SECRET_KEY` in `config.py` to a strong random value, and review file upload limits.
- Face encodings and photos are personal biometric data — handle the `instance/` and `static/uploads/` folders accordingly, and make sure your institution's data protection policies are followed before deploying with real students.

---

## 🛣 Roadmap ideas

- Password reset flow
- Bulk CSV import for enrolling many students at once
- Lecturer analytics dashboard (attendance trends over time)
- Push/email notifications when a student drops below the eligibility threshold
- Multi-photo enrollment for more robust face matching across lighting conditions

---

## 📄 License

MIT — do whatever you'd like with this, attribution appreciated.
