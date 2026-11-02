#!/bin/bash
# One command to start the demo: database check, API, UI.   Usage: ./run_demo.sh
cd "$(dirname "$0")"
PY=.venv/bin/python

# 1. Database (local Homebrew PostgreSQL, or Docker if available)
if ! $PY -c "from app.core.db import engine; engine.connect()" 2>/dev/null; then
  echo "Starting database..."
  if command -v docker >/dev/null && [ -f docker-compose.yml ]; then
    docker compose up -d && sleep 8
  else
    brew services start postgresql@17 >/dev/null 2>&1; sleep 4
  fi
fi
$PY -m scripts.init_db >/dev/null || { echo "Database is not reachable"; exit 1; }

# 2. Sample data on first run
[ -f data/raw/hygiene_hands.pdf ] || $PY -m scripts.make_sample_corpus
$PY -m scripts.load_corpus | grep -v skipped

# 3. API in the background, UI in the foreground
.venv/bin/uvicorn app.main:app --port 8000 >/tmp/medai_api.log 2>&1 &
API_PID=$!
trap "kill $API_PID 2>/dev/null" EXIT
sleep 6
echo "API: http://localhost:8000/docs   UI: http://localhost:8501"
(sleep 5 && open http://localhost:8501) >/dev/null 2>&1 &
.venv/bin/streamlit run ui/streamlit_app.py --server.port 8501 --server.headless true \
  --browser.gatherUsageStats false
