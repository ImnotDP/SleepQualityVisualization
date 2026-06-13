#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Python venv
if [ ! -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    python3 -m venv "$SCRIPT_DIR/.venv"
    "$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q
fi

cd "$SCRIPT_DIR/frontend"
[ -d "node_modules" ] || npm install
npm run build

cd "$SCRIPT_DIR/backend"
"$SCRIPT_DIR/.venv/bin/python" app.py &
BACKEND_PID=$!

cd "$SCRIPT_DIR/frontend"
node serve.cjs &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
