#!/usr/bin/env bash
# Start IsoFold Trace locally: the Python engine + API, which also serves the built web app.
#   ./run.sh            -> http://localhost:8765
#   PORT=9000 ./run.sh  -> another port
set -euo pipefail
cd "$(dirname "$0")"
PY="$(cd .. && pwd)/.venv/bin/python"
[ -x "$PY" ] || { echo "No Python venv at IsoFold/.venv (see backend/requirements.txt)"; exit 1; }

# build the web app if it was never built or its source changed since
if [ -f web/package.json ] && { [ ! -d web/dist ] || [ -n "$(find web/src web/index.html -newer web/dist/index.html -print -quit)" ]; }; then
  echo "Building the web app…"
  (cd web && npm run build)
fi

echo "IsoFold Trace → http://localhost:${PORT:-8765}"
cd backend && exec "$PY" -m uvicorn api:app --host 127.0.0.1 --port "${PORT:-8765}"
