@echo off
title NutriVeda - Backend Server
echo ============================================
echo   NutriVeda System - Backend (FastAPI)
echo ============================================
echo.

cd /d "%~dp0backend"

:: Add Python user scripts to PATH (for uvicorn, etc.)
set PATH=%APPDATA%\Python\Python314\Scripts;%PATH%

echo [1/2] Verifying dependencies...
python -c "import fastapi, openai, numpy; print('  All dependencies OK')"
if errorlevel 1 (
    echo Installing missing packages...
    pip install -r requirements.txt --only-binary :all: -q
)

echo.
echo [2/2] Starting FastAPI server...
echo       Backend URL: http://localhost:8000
echo       API Docs:    http://localhost:8000/docs
echo       Admin UI:    http://localhost/admin
echo.
echo Press Ctrl+C to stop the server
echo.
python main.py
pause
