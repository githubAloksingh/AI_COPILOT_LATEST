@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -Command "$h = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2 -ErrorAction Stop; if ($h.service -eq 'ai-service' -and $h.status -eq 'healthy') { exit 0 }; exit 1" >nul 2>nul
if %errorlevel% equ 0 (
    echo AI service is already running and healthy at http://127.0.0.1:8000.
    exit /b 0
)
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) else (
    echo Could not find AI service virtual environment at "%VENV_PYTHON%"
    echo Falling back to system Python.
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
)
