# Medical AI Assistant

An internal AI assistant for hospital staff: ask questions about medical protocols in Hebrew and get answers with document and page citations, plus an AI agent that can search protocols, query their metadata with read-only SQL, and build checklists.

> **Data:** public Ministry of Health circulars and synthetic documents only. No real patient data.
> This is an engineering demo, not a tool for medical decisions.

**Stack:** Python · FastAPI · PostgreSQL + pgvector · RAG · LLM tool calling · Docker

## Status

| Day | Scope | Status |
|---|---|---|
| 1 | Project setup, database, Hebrew PDF extraction | ✅ Done |
| 2 | FastAPI backend, chunking, embeddings | ✅ Done |
| 3 | RAG answers with citations, prompt engineering | ✅ Done |
| 4 | AI agent with 3 tools | ✅ Done |
| 5 | Evaluation, UI, demo | ✅ Done |

## Architecture

```
Streamlit / Swagger ──► FastAPI ──► AI Agent ──► LLM API
                           │            │
                     upload PDF    picks a tool
                           ▼            ▼
                 Document ingestion   Agent tools
                           │            │
                           ▼            ▼
                    PostgreSQL + pgvector
        documents · chunks (vectors) · queries · agent_steps
```

## Demo in one command

```bash
./run_demo.sh      # database check + sample data + API (:8000) + UI (:8501)
```

The UI has four tabs: **Search** (works without an LLM key), **Ask** (RAG answer with document + page
citations), **Agent** (shows every tool call it makes) and **Documents** (list and upload PDFs).

## Run everything with Docker

Requirements: Docker only.

```bash
cp .env.example .env        # set the passwords, and LLM_PROVIDER / LLM_API_KEY for Ask and Agent
docker compose up --build   # db + api (:8000) + ui (:8501)
```

Open http://localhost:8501 for the UI and http://localhost:8000/docs for the API.
On first start the API container creates the tables, generates the sample Hebrew protocols and
indexes them. PDFs live in `./data/raw` on your machine (mounted into the container).
If a local PostgreSQL already uses port 5432, publish the database on another port:
`DB_HOST_PORT=5433 docker compose up --build`.

| Service | Image | What it does |
|---|---|---|
| `db` | `pgvector/pgvector:pg16` | PostgreSQL + pgvector, read-only agent role from `db/init.sh` |
| `api` | built from `Dockerfile` | FastAPI; runs `docker/start-api.sh` (init DB, load PDFs, serve) |
| `ui` | same image | Streamlit, calls the API at `http://api:8000` |

The image uses CPU-only PyTorch, bakes in the embedding model, and runs as a non-root user.
Secrets come from `.env` at runtime and are excluded from the image by `.dockerignore`.

Run tests and the eval inside the container:

```bash
docker compose exec api pytest
docker compose exec api python -m eval.run_eval
```

## Local development (without Docker for the app)

Requirements: Python 3.11+, Docker (for the database).

```bash
# 1. Environment
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # then edit the passwords

# 2. Database (PostgreSQL 16 + pgvector)
docker compose up -d
python -m scripts.init_db
# -> Tables ready: agent_steps, chunks, documents, queries

# 3. Sample data: 5 synthetic Hebrew protocols (half stored in visual order)
python -m scripts.make_sample_corpus
python -m scripts.check_pdf_hebrew       # does Hebrew come out readable?
python -m scripts.load_corpus            # extract -> chunk -> embed -> store

# 4. Run
uvicorn app.main:app --reload            # API + Swagger at http://localhost:8000/docs
streamlit run ui/streamlit_app.py        # UI

# 5. Quality
pytest                                   # unit + integration tests
python -m eval.run_eval                  # retrieval quality (hit@k, MRR), no API key needed
```

Set `LLM_PROVIDER` (`anthropic` or `openai`) and `LLM_API_KEY` in `.env` to enable `/ask` and `/agent`.
Search, upload and the eval work without a key.

Without Docker you can use a local PostgreSQL 16/17 with the `pgvector` extension instead; create the
`agent_readonly` role as in `db/init.sh` and run `python -m scripts.init_db`.

## Engineering notes

### Hebrew PDF extraction (Day 1)

Many Israeli PDFs store Hebrew in *visual* order, so extracted text comes out reversed ("להונ" instead of "נוהל"). Embedding reversed text would silently break search.

- **Detection:** Hebrew final letters (ך ם ן ף ץ) only appear at the end of a word. If most of them appear at the start, the text is reversed.
- **Fix:** reverse the line, then restore left-to-right runs (numbers, dates like `12/2024`, English like `EMR`).
- **Library choice:** PyMuPDF applies its own bidi reordering, which moves numbers, English and punctuation to the wrong side of Hebrew lines. pdfplumber returns characters in stored order, which the fixer handles correctly. The app therefore uses pdfplumber; a strict `xfail` test documents the PyMuPDF behavior.

### RAG and citations (Day 3)

Retrieved chunks are numbered `[1]..[n]` in the prompt with document title and page. The model must cite
`[n]` after every claim, and the API maps those back to `(document, page)`. If nothing relevant is found the
prompt instructs it to say so instead of guessing. Instructions inside retrieved text are explicitly ignored
(prompt-injection guard). Every question, answer, source list and latency is stored in `queries`.

### Agent and SQL safety (Day 4)

Tools: `search_protocols`, `query_metadata_sql`, `build_checklist`. The loop is capped at 6 steps and every
tool call is stored in `agent_steps`. LLM-written SQL passes three layers: (1) a validator allowing one
`SELECT` on `documents` only, (2) a DB role (`agent_readonly`) with `SELECT` on `documents` only, (3) a
`READ ONLY` transaction with a 5 s timeout and a 50-row cap.

### Database

- `chunks.embedding` is a `vector(384)` with an **HNSW** index (cosine distance).
- Embedding model: `intfloat/multilingual-e5-small` (runs locally, supports Hebrew, no API cost).
- `db/init.sh` creates an **`agent_readonly`** user with `SELECT` only. The agent's SQL tool (Day 4) connects as this user, so a bad generated query cannot modify data.

## Project structure

```
app/
  main.py            FastAPI entry point
  api/               routers: documents (upload/list/search), qa (ask/agent/query log)
  core/              settings, database engine/session
  ingestion/         pdf_utils (Hebrew fix), chunking, pipeline (PDF -> DB)
  retrieval/         embeddings, vector search
  llm.py             provider-neutral client (Anthropic / OpenAI) with tool calling
  prompts.py         all prompts in one place
  rag.py             retrieve -> answer with [n] citations -> log
  agent/             loop, 3 tools, SQL safety validator
  models.py          documents, chunks, queries, agent_steps
db/init.sh           pgvector + read-only DB user (first container start)
scripts/             init_db, make_sample_corpus, load_corpus, check_pdf_hebrew
eval/                questions.json + run_eval (hit@k, MRR)
ui/                  Streamlit app
tests/               pytest suite
```
