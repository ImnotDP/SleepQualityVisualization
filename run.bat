@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

where node >nul 2>&1
if %errorlevel% neq 0 (echo Node.js not found & pause & exit /b 1)

:: Python venv
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo Setting up Python venv...
    python -m venv "%SCRIPT_DIR%.venv"
    if %errorlevel% neq 0 (echo venv create failed & pause & exit /b 1)
    call "%SCRIPT_DIR%.venv\Scripts\activate"
    python -m pip install -r "%SCRIPT_DIR%requirements.txt" -q
    if %errorlevel% neq 0 (echo pip install failed & pause & exit /b 1)
)
set PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe

:: build frontend
cd /d "%SCRIPT_DIR%frontend"
if not exist "node_modules" (
    call npm install >nul 2>&1
    if %errorlevel% neq 0 (echo npm install failed & pause & exit /b 1)
)
call npm run build >nul 2>&1
if %errorlevel% neq 0 (echo npm run build failed & pause & exit /b 1)

:: start backend
cd /d "%SCRIPT_DIR%backend"
start "Backend" cmd /c "cd /d "%SCRIPT_DIR%backend" && "%PYTHON%" app.py"

:: start frontend
cd /d "%SCRIPT_DIR%frontend"
start "Frontend" /MIN cmd /c "cd /d "%SCRIPT_DIR%frontend" && node serve.cjs"

:: 等待后端完全启动（轮询 :5000 端口，最多等 60 秒）
echo Waiting for backend to start...
set /a RETRIES=0
:wait_backend
ping -n 2 127.0.0.1 >nul
curl -s -o nul http://127.0.0.1:5000/api/status 2>nul && goto backend_ready
set /a RETRIES+=1
if %RETRIES% lss 30 goto wait_backend
echo [WARNING] Backend took too long, opening anyway...
:backend_ready
echo Backend is ready!
start "" "http://localhost:3000"
