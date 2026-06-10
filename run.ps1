$ErrorActionPreference = "Stop"

$ENV_NAME = "sleepQualityVisualization"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---------- read config ----------
$configPath = Join-Path $SCRIPT_DIR "backend\config.txt"
$config = @{}
if (Test-Path $configPath) {
    Get-Content $configPath | ForEach-Object {
        if ($_ -match '^([^#].*?)=(.*)') { $config[$Matches[1].Trim()] = $Matches[2].Trim() }
    }
}
$FRONTEND_PORT = if ($config["FRONTEND_PORT"]) { $config["FRONTEND_PORT"] } else { "3000" }

# ---------- dependency checks ----------
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] conda not found, install Anaconda first"
    Pause; exit 1
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Node.js not found, install Node.js >= 18 first"
    Pause; exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] npm not found"
    Pause; exit 1
}

# ---------- conda env ----------
$condaBase = conda info --base 2>&1
$activateScript = Join-Path $condaBase "shell\condabin\conda-hook.ps1"
if (Test-Path $activateScript) { . $activateScript }

$envList = conda env list 2>&1
if ($envList -match $ENV_NAME) {
    conda env update -f environment.yml --prune -q
} else {
    conda env create -f environment.yml -q
}
conda activate $ENV_NAME

# ---------- frontend ----------
Set-Location (Join-Path $SCRIPT_DIR "frontend")
if (-not (Test-Path "node_modules")) { npm install --silent }
npm run build --silent
Set-Location $SCRIPT_DIR

# ---------- cleanup ----------
$global:BackendJob = $null
$global:FrontendJob = $null
function Cleanup {
    if ($global:BackendJob)  { Stop-Job -Job $global:BackendJob  -ErrorAction SilentlyContinue; Remove-Job -Job $global:BackendJob  -ErrorAction SilentlyContinue }
    if ($global:FrontendJob) { Stop-Job -Job $global:FrontendJob -ErrorAction SilentlyContinue; Remove-Job -Job $global:FrontendJob -ErrorAction SilentlyContinue }
}

# ---------- start services ----------
$global:BackendJob = Start-Job -Name "FlaskBackend" -ScriptBlock {
    param($dir); Set-Location $dir; python app.py
} -ArgumentList (Join-Path $SCRIPT_DIR "backend")
Start-Sleep -Seconds 3

if ((Get-Job -Name "FlaskBackend").State -eq "Failed") {
    Write-Host "[ERROR] Flask backend failed to start"
    Get-Job -Name "FlaskBackend" | Receive-Job
    Pause; exit 1
}

$global:FrontendJob = Start-Job -Name "FrontendServer" -ScriptBlock {
    param($dir); Set-Location $dir; node serve.cjs
} -ArgumentList (Join-Path $SCRIPT_DIR "frontend")
Start-Sleep -Seconds 2

# ---------- open browser ----------
$FRONTEND_URL = "http://localhost:$FRONTEND_PORT"
Start-Process $FRONTEND_URL
Write-Host $FRONTEND_URL

try {
    while ($true) {
        if ((Get-Job -Name "FlaskBackend" -ErrorAction SilentlyContinue).State -eq "Failed") {
            Write-Host "[ERROR] Flask backend crashed"
            Get-Job -Name "FlaskBackend" | Receive-Job
            break
        }
        if ((Get-Job -Name "FrontendServer" -ErrorAction SilentlyContinue).State -eq "Failed") {
            Write-Host "[ERROR] Frontend server crashed"
            Get-Job -Name "FrontendServer" | Receive-Job
            break
        }
        Start-Sleep -Seconds 5
    }
} finally { Cleanup }
Pause
