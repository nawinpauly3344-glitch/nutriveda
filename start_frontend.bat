@echo off
title NutriVeda - Frontend Server
echo ============================================
echo   NutriVeda System - Frontend (Next.js)
echo ============================================
echo.
echo Frontend will run on: http://localhost  (Port 80)
echo No port number needed in your browser!
echo.
echo NOTE: If port 80 fails with "permission denied",
echo right-click this bat file and "Run as Administrator"
echo.

cd /d "%~dp0frontend"

echo [1/2] Installing dependencies (first time only)...
npm install --silent

echo.
echo [2/2] Starting Next.js on http://localhost (port 80)
echo       Press Ctrl+C to stop
echo.
npx next dev --port 80
pause
