#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
cd backend && python app.py &
cd "$SCRIPT_DIR"
cd frontend && node serve.cjs &
wait
