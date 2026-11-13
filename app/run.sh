#!/usr/bin/env bash
# Start IsoFold Trace locally: the Python engine + API, which also serves the built web app.
#   ./run.sh            -> http://localhost:8000
#   PORT=9000 ./run.sh  -> another port
set -euo pipefail
cd "$(dirname "$0")"
PY=../.venv/bin/python
[ -x "$PY" ] || { echo "No Python venv at IsoFold/.venv (see backend/requirements.txt)"; exit 1; }

if [ -f web/package.json ] && [ ! -d web/dist ]; then
  echo "Building the web app…"
  (cd web && npm run build)
fi

echo "IsoFold Trace → http://localhost:${PORT:-8000}"
cd backend && exec "$PY" -m uvicorn api:app --host 127.0.0.1 --port "${PORT:-8000}"
