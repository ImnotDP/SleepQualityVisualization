#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
ENV_NAME="sleepQualityVisualization"

# ---------- read config ----------
_get_config() {
  local key=$1
  grep "^${key}=" "$SCRIPT_DIR/backend/config.txt" 2>/dev/null | cut -d= -f2-
}
FRONTEND_PORT=$(_get_config "FRONTEND_PORT")
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# ---------- dependency checks ----------
command -v conda &>/dev/null || { echo "[ERROR] conda not found, install Anaconda first"; exit 1; }
command -v node  &>/dev/null || { echo "[ERROR] Node.js not found, install Node.js >= 18 first"; exit 1; }
command -v npm   &>/dev/null || { echo "[ERROR] npm not found"; exit 1; }

# ---------- conda env ----------
CONDA_BASE="$(conda info --base 2>/dev/null)"
[ -f "$CONDA_BASE/etc/profile.d/conda.sh" ] && source "$CONDA_BASE/etc/profile.d/conda.sh"

if conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
  conda env update -f environment.yml --prune -q
else
  conda env create -f environment.yml -q
fi
conda activate "$ENV_NAME"

# ---------- frontend ----------
cd frontend
[ ! -d "node_modules" ] && npm install --silent
npm run build --silent
cd "$SCRIPT_DIR"

# ---------- start services ----------
cleanup() {
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

cd backend && python app.py &
BACKEND_PID=$!
cd "$SCRIPT_DIR"
sleep 2

cd frontend && node serve.cjs &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"
sleep 1

# ---------- open browser ----------
FRONTEND_URL="http://localhost:${FRONTEND_PORT}"
if [[ "$OSTYPE" == "darwin"* ]]; then
  open "$FRONTEND_URL"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  xdg-open "$FRONTEND_URL" 2>/dev/null || true
fi

echo "http://localhost:${FRONTEND_PORT}"
wait
