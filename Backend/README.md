# OpenReconFi — Backend

Self-hosted agency finance ops: invoice collection, bank reconciliation, vendor management, reports, and expense chat (RAG).

## Prerequisites

- Docker & Docker Compose
- API keys: [Anthropic](https://console.anthropic.com/) + [OpenAI](https://platform.openai.com/)
- Google Cloud project with Gmail API + Drive API enabled

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
```

Fill in your `.env`:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key — used for invoice extraction, bank statement parsing, matching, and chat |
| `OPENAI_API_KEY` | OpenAI API key — used for `text-embedding-3-small` embeddings (RAG chat) |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID (Desktop app type) |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret |
| `GOOGLE_REFRESH_TOKEN` | OAuth refresh token (see below) |
| `DRIVE_INVOICES_FOLDER_ID` | Google Drive folder ID for invoice + report storage |

### 2. Get Google refresh token

Create an OAuth 2.0 Client ID (type: **Desktop app**) in [Google Cloud Console](https://console.cloud.google.com/apis/credentials), then run:

```bash
uv run python scripts/get_google_refresh_token.py
```

This opens a browser for consent and prints your `GOOGLE_REFRESH_TOKEN`. Paste it into `.env`.

### 3. Get Drive folder ID

Create a folder in Google Drive (e.g. `OpenReconFi`). Open it and grab the ID from the URL:

```
https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ
                                       └── this is your DRIVE_INVOICES_FOLDER_ID
```

### 4. Start everything

```bash
docker compose up --build
```

This will:
1. Start Postgres (pgvector-enabled) and wait for it to be healthy
2. Auto-create the `vector` extension (via init script)
3. Run all Alembic migrations
4. Start the FastAPI server

Backend is live at **http://localhost:8000/docs** (Swagger UI).

## API Overview

| Endpoint | Description |
|---|---|
| `POST /jobs/trigger` | Trigger Gmail sync or portal scrape |
| `GET /invoices` | List invoices |
| `POST /invoices` | Manual invoice upload |
| `POST /reconciliation/upload` | Upload bank statement (XLS/CSV/MT940/CAMT.053) |
| `POST /reconciliation/match` | LLM-match transactions to invoices |
| `GET /vendors` | Vendor management (CRUD + billing cycles) |
| `GET /dashboard/spend-summary` | Spending overview |
| `POST /reports/generate` | Generate PDF/Excel report (also uploads to Drive) |
| `POST /chat/message` | Expense chat (RAG, streaming SSE) |

## Development

### Run locally (without Docker)

```bash
# Start just Postgres
docker compose up postgres -d

# Create pgvector extension (first time only)
docker exec openreconfi-postgres-1 psql -U openreconfi -d openreconfi -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
uv run alembic upgrade head

# Start server
uv run uvicorn app.main:app --reload --port 8000
```

### Run tests

```bash
# Create test database (first time only)
docker exec openreconfi-postgres-1 psql -U openreconfi -c "CREATE DATABASE openreconfi_test;"
docker exec openreconfi-postgres-1 psql -U postgres -d openreconfi_test -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run tests
uv run pytest tests/ -v
```

### Backfill embeddings

After populating invoices/transactions, run the backfill to enable RAG chat:

```bash
uv run python scripts/backfill_embeddings.py
```

After backfill, create the vector index for faster searches:

```sql
CREATE INDEX ON invoices USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON transactions USING ivfflat (embedding vector_cosine_ops);
```

## Project Structure

```
app/
├── config.py              # Pydantic settings (.env)
├── db.py                  # Async SQLAlchemy session
├── main.py                # FastAPI app
├── models/                # SQLAlchemy models
├── schemas/               # Pydantic request/response schemas
├── routers/               # API endpoints
├── services/              # Business logic
│   ├── collector.py       # Gmail → extract → rename → store → Drive
│   ├── gmail.py           # Gmail API
│   ├── drive.py           # Google Drive API
│   ├── llm.py             # Claude API (extraction, parsing, matching)
│   ├── reporter.py        # PDF (WeasyPrint) + Excel (openpyxl) reports
│   ├── embeddings.py      # OpenAI embeddings
│   ├── chat.py            # RAG chat pipeline
│   └── ingester.py        # Bank statement parsing (XLS/CSV/MT940/CAMT.053)
├── scrapers/              # Portal scraper framework
scripts/
├── entrypoint.sh          # Docker entrypoint (migrate + serve)
├── backfill_embeddings.py # One-shot embedding backfill
├── get_google_refresh_token.py  # OAuth helper
├── init-pgvector.sql      # Postgres init script
tests/                     # pytest-asyncio test suite
```
