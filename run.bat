@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

:: start backend
start "Backend" /MIN cmd /c "cd /d "%SCRIPT_DIR%backend" && python app.py"
:: start frontend
start "Frontend" /MIN cmd /c "cd /d "%SCRIPT_DIR%frontend" && node serve.cjs"
:: open browser
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"
