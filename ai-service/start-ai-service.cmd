@echo off
setlocal
cd /d "%~dp0"
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo Could not find AI service virtual environment at "%VENV_PYTHON%"
    echo Falling back to system Python.
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)
