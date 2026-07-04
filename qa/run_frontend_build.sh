#!/usr/bin/env bash
# Frontend QA: production build (react-scripts) in a Node 20 container.
# No local Node needed.
#   ./qa/run_frontend_build.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd -W 2>/dev/null || pwd)"

MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$REPO/frontend:/app" -w /app \
  -e CI=false \
  node:20-alpine sh -c "npm install --no-audit --no-fund --loglevel=error && npm run build"

echo "frontend build passed"
