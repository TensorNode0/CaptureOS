#!/usr/bin/env bash
# Backend QA: spins up Postgres 16 + the FastAPI server in Docker and runs the
# full pytest suite against it. No local Python needed.
#   ./qa/run_backend_tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd -W 2>/dev/null || pwd)"

NET=captureagent-qa-net
PG=captureagent-qa-pg

docker rm -f "$PG" >/dev/null 2>&1 || true
docker network rm "$NET" >/dev/null 2>&1 || true
docker network create "$NET" >/dev/null

cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_PASSWORD=postgres postgres:16-alpine >/dev/null

MSYS_NO_PATHCONV=1 docker run --rm --network "$NET" \
  -v "$REPO:/repo" \
  -e QA_PG_HOST="$PG" \
  -e DATABASE_URL="postgresql://postgres:postgres@$PG:5432/postgres" \
  -e SUPABASE_JWT_SECRET=qa-test-secret \
  -e AUTH_TEST_MODE=1 \
  -e SECRETS_ENC_KEY="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=" \
  -e SEED_DEMO=1 \
  -e FRONTEND_URL=http://localhost:3000 \
  python:3.12-slim bash /repo/qa/_backend_container.sh

echo "backend QA passed"
