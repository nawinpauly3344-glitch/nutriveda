@echo off
title NutriVeda - Public Internet Access (ngrok)
echo ============================================
echo   NutriVeda - Public Internet Tunnel
echo ============================================
echo.
echo IMPORTANT: Make sure these are already running first:
echo   1. start_backend.bat
echo   2. start_frontend.bat (Run as Administrator)
echo.
echo Starting public tunnel on your static ngrok domain...
echo Your clients can visit the URL shown below.
echo.

:: Replace YOUR-DOMAIN with your actual ngrok static domain
:: Get it free from: https://dashboard.ngrok.com/cloud-edge/domains
ngrok http --domain=YOUR-DOMAIN.ngrok-free.app 80

pause
