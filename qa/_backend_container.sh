#!/usr/bin/env bash
# Runs INSIDE the python:3.12-slim container (see run_backend_tests.sh).
set -e
cd /repo/backend

pip install -q -r requirements.txt -r requirements-dev.txt

python - <<'PY'
import os, socket, time
host = os.environ.get("QA_PG_HOST", "captureagent-qa-pg")
for _ in range(60):
    try:
        socket.create_connection((host, 5432), 1).close()
        break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("postgres not reachable")
PY

uvicorn server:app --host 0.0.0.0 --port 8000 > /tmp/server.log 2>&1 &

python - <<'PY'
import time, urllib.request
for _ in range(90):
    try:
        urllib.request.urlopen("http://localhost:8000/api/health", timeout=2)
        break
    except Exception:
        time.sleep(1)
else:
    print(open("/tmp/server.log").read())
    raise SystemExit("server did not become healthy")
PY

if ! pytest tests -q; then
  echo "--- server log (tail) ---"
  tail -80 /tmp/server.log
  exit 1
fi
