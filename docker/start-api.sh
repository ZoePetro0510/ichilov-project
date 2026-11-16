#!/bin/sh
# API container entry point: same steps as run_demo.sh, inside Docker.
set -e

# 1. Tables + read-only grants (safe to run on every start)
python -m scripts.init_db

# 2. Sample data on first run, then ingest any PDF not loaded yet
[ -f data/raw/hygiene_hands.pdf ] || python -m scripts.make_sample_corpus
python -m scripts.load_corpus | grep -v skipped || true

# 3. API
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
