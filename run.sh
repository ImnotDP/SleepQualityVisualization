#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ---------- detect Python ----------
if command -v conda &>/dev/null && conda env list 2>/dev/null | grep -q "sleepQualityVisualization"; then
    echo "[INFO] Using conda environment: sleepQualityVisualization"
    PYTHON="$(conda run -n sleepQualityVisualization which python)"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    echo "[INFO] Using existing venv"
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
else
    echo "[INFO] Creating Python venv..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
    "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

# ---------- frontend ----------
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    npm install
fi
echo "[INFO] Building frontend..."
npm run build

# ---------- backend ----------
cd "$SCRIPT_DIR/backend"
echo "[INFO] Starting backend on http://127.0.0.1:5000 ..."
"$PYTHON" app.py &
BACKEND_PID=$!

# wait for backend to be ready
echo "[INFO] Waiting for backend..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:5000/api/status >/dev/null 2>&1; then
        echo "[INFO] Backend is ready!"
        break
    fi
    sleep 1
done

# ---------- frontend server ----------
cd "$SCRIPT_DIR/frontend"
echo "[INFO] Starting frontend on http://localhost:3000 ..."
node serve.cjs &
FRONTEND_PID=$!

# ---------- open browser ----------
sleep 1
open "http://localhost:3000" 2>/dev/null || echo "[INFO] Open http://localhost:3000 in your browser"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
