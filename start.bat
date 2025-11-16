@echo off
ECHO Starting application setup...

REM Check for virtual environment
IF NOT EXIST venv (
    ECHO Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
ECHO Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
ECHO Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM Check and populate database if it doesn't exist
IF NOT EXIST travel_crm.db (
    ECHO Database not found. Running populate_db.py...
    python populate_db.py
)

ECHO Starting Flask application...
python run.py
