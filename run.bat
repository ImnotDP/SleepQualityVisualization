@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set ENV_NAME=sleepQualityVisualization
set SCRIPT_DIR=%~dp0

:: ---------- read config ----------
for /f "tokens=2 delims==" %%a in ('findstr /b "FRONTEND_PORT=" "%SCRIPT_DIR%backend\config.txt" 2^>nul') do set FRONTEND_PORT=%%a
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=3000

:: ---------- dependency checks ----------
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] conda not found, install Anaconda first
    pause
    exit /b 1
)
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found, install Node.js ^>= 18 first
    pause
    exit /b 1
)
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found
    pause
    exit /b 1
)

:: ---------- conda env ----------
call "%USERPROFILE%\miniconda3\Scripts\activate.bat" 2>nul || call "%USERPROFILE%\anaconda3\Scripts\activate.bat" 2>nul || call "%USERPROFILE%\miniforge3\Scripts\activate.bat" 2>nul

conda env list 2>nul | findstr /c:"%ENV_NAME% " >nul
if %errorlevel% equ 0 (
    call conda env update -f environment.yml --prune -q
) else (
    call conda env create -f environment.yml -q
)
call conda activate %ENV_NAME%

:: ---------- frontend ----------
cd /d "%SCRIPT_DIR%frontend"
if not exist "node_modules" call npm install --silent
call npm run build --silent
cd /d "%SCRIPT_DIR%"

:: ---------- start services ----------
start "Flask-Backend" /MIN cmd /c "cd /d "%SCRIPT_DIR%backend" && python app.py"
timeout /t 3 /nobreak >nul
start "Frontend-Server" /MIN cmd /c "cd /d "%SCRIPT_DIR%frontend" && node serve.cjs"
timeout /t 2 /nobreak >nul

:: ---------- open browser ----------
start "" "http://localhost:%FRONTEND_PORT%"
echo http://localhost:%FRONTEND_PORT%
pause
