#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Building frontend..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build

cd "$PROJECT_DIR"

# Activate virtualenv if present
if [[ -f venv/bin/activate ]]; then
    source venv/bin/activate
elif [[ -f .venv/bin/activate ]]; then
    source .venv/bin/activate
fi

echo "Starting Jailbreaking Challenge app on http://127.0.0.1:8000 ..."
uvicorn backend.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --log-level info
