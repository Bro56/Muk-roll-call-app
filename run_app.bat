@echo off
setlocal enabledelayedexpansion
title Makerere Roll Call - Setup and Launch
cd /d "%~dp0"

echo ============================================
echo   Makerere University Roll Call
echo   Setup and Launch
echo ============================================
echo.

REM --- Check Python is installed ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on your PATH.
    echo Please install Python 3.10 or 3.11 from https://www.python.org/downloads/
    echo IMPORTANT: during install, tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

REM --- Create virtual environment if missing ---
if not exist "venv\" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/4] Virtual environment already exists, skipping creation.
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies (this can take a while the first time,
echo        especially dlib/face_recognition which compiles from source)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [WARNING] Something failed while installing dependencies.
    echo This is almost always the dlib/face_recognition install on Windows.
    echo See the "Troubleshooting: face_recognition on Windows" section of README.md
    echo for the CMake / Visual C++ Build Tools / conda instructions.
    echo.
    pause
    exit /b 1
)

echo [4/4] Launching Roll Call...
echo.
echo   The app will open automatically in your browser at:
echo   http://127.0.0.1:5000
echo.
echo   Default admin login -> username: admin   password: admin123
echo   (change this after your first login)
echo.
echo   Press CTRL+C in this window to stop the server.
echo ============================================
echo.

python app.py

pause
