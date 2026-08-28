#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  Makerere University Roll Call"
echo "  Setup and Launch"
echo "============================================"
echo

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 was not found. Please install Python 3.10 or 3.11."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/4] Virtual environment already exists, skipping creation."
fi

echo "[2/4] Activating virtual environment..."
source venv/bin/activate

echo "[3/4] Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

echo "[4/4] Launching Roll Call at http://127.0.0.1:5000"
echo "Default admin login -> username: admin   password: admin123"
echo "Press CTRL+C to stop the server."
echo

python app.py
