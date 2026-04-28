#!/usr/bin/env bash
# Usage: ./infra/tunnel.sh <user@gpunode>
# Opens SSH tunnel: localhost:8001 -> gpunode:8000
set -euo pipefail

REMOTE="${1:?Usage: $0 user@gpunode}"
LOCAL_PORT=8001
REMOTE_PORT=8000

echo "Opening SSH tunnel: localhost:${LOCAL_PORT} -> ${REMOTE}:${REMOTE_PORT}"
echo "Press Ctrl+C to close."

ssh -NL "${LOCAL_PORT}:localhost:${REMOTE_PORT}" "${REMOTE}"
