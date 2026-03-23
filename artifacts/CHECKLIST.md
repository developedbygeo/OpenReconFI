# Matchbook — Build Checklist

> **Implementation note — pgvector IVFFlat index**
>
> The `embedding vector(1024)` columns exist on `invoices` and `transactions`, but the IVFFlat
> index must be created **after** running `scripts/backfill_embeddings.py`. IVFFlat builds cluster
> centroids at `CREATE INDEX` time from existing data — creating it on an empty table produces
> poor centroids and degrades search quality. Once the backfill is complete, run:
>
> ```sql
> CREATE INDEX ON invoices USING ivfflat (embedding vector_cosine_ops);
> CREATE INDEX ON transactions USING ivfflat (embedding vector_cosine_ops);
> ```
>
> This can be a standalone Alembic migration or manual SQL.

---

## Phase 1 — Collection Pipeline

### Infrastructure
- [x] `docker-compose.yml` — postgres, backend, frontend, nginx services
- [ ] `nginx.conf` — reverse proxy config
- [ ] `.env.example` — all required variables documented
- [x] Postgres running, migrations baseline established

### Backend — Database
- [x] SQLAlchemy models: `Invoice`, `Vendor`, `Category`, `JobRun`
- [x] Alembic initial migration — all Phase 1 tables
- [x] `db.py` — async session, connection pool

### Backend — Gmail + Drive
- [x] `gmail.py` — OAuth setup, fetch unread emails with PDF attachments
- [x] `drive.py` — upload file, create folder structure `/Invoices/YYYY/Month/`
- [x] `collector.py` — orchestrates fetch → extract → rename → store → upload

### Backend — LLM Extraction
- [x] `llm.py` — extraction prompt, call Claude API, parse JSON response
- [x] Structured filename rename: `2026-03_Vercel_€49.00_INV-1234.pdf`
- [x] `raw_extraction` jsonb stored for debugging

### Backend — Routers
- [x] `routers/invoices.py` — list, detail, manual upload; all routes have `response_model=` and `tags=["invoices"]`
- [x] `routers/jobs.py` — trigger gmail sync, get job status; `tags=["jobs"]`
- [x] `export_schema.py` — dumps `openapi.json` without starting server

### Backend — Tests
- [x] `conftest.py` — test DB, async client, mocks for Claude API / Gmail / Drive
- [x] `test_invoices.py`
- [x] `test_llm.py` — extraction prompt + response parsing
- [x] `test_gmail.py`

### Frontend — Type Generation
- [x] `orval.config.ts` — input `../openapi.json`, output `src/api/`, mode `tags-split`
- [x] `pnpm generate:api` script in `package.json`
- [x] `src/api/` generates cleanly: `types.ts`, `invoices.ts`, `jobs.ts`

### Frontend — Collection UI
- [x] Invoice list view — vendor, amount, date, status, Drive link
- [x] Invoice detail view — all fields, raw extraction toggle
- [x] Collection page — trigger Gmail sync button, job status / log display
- [x] MSW handlers for invoices + jobs

---

## Phase 2 — Reconciliation

### Backend — Statement Ingestion
- [x] `ingester.py` — XLS/XLSX → CSV string via openpyxl
- [x] `ingester.py` — MT940 → text via mt940 lib
- [x] `ingester.py` — CAMT.053 → text via XML parse
- [x] `ingester.py` — CSV → decoded text
- [x] `test_ingester.py` — one test per format

### Backend — LLM Parsing + Matching
- [x] `llm.py` — statement parsing prompt, handles signed / debit+credit / unsigned+type columns
- [x] `llm.py` — matching prompt, returns confidence + rationale per pair
- [x] Transaction model + Alembic migration
- [x] Match model + Alembic migration
- [x] Type casting + validation after LLM parse: `numeric(10,2)`, date, required fields
- [x] `test_llm.py` — statement parsing + matching prompt tests

### Backend — Routers
- [x] `routers/reconciliation.py` — upload statement, trigger match, confirm, reject, reassign; `tags=["reconciliation"]`
- [x] `test_reconciliation.py`
- [x] Regenerate `openapi.json` + `pnpm generate:api`

### Backend — Vendor Aliases
- [x] Alias learning: on confirmed match, save bank description variant to `vendors.aliases`

### Frontend — Reconciliation UI
- [x] Bank statement upload (Mantine Dropzone) — XLS/XLSX/CSV/MT940/CAMT.053
- [x] Match review UI — confidence score, rationale, confirm / reject / reassign per pair
- [x] Exception flagging UI
- [x] MSW handlers for reconciliation

---

## Phase 3 — Vendor Management + Billing Cycles

### Backend
- [x] `routers/vendors.py` — CRUD, set billing cycle, view invoice history; `tags=["vendors"]`
- [x] Missing invoice detection — calculated at query time from `billing_cycle` + last invoice date
- [x] `routers/dashboard.py` — missing invoice alerts endpoint; `tags=["dashboard"]`
- [x] `test_vendors.py` — billing cycle logic, missing invoice detection edge cases
- [x] `test_dashboard.py` — alert aggregation
- [x] Regenerate `openapi.json` + `pnpm generate:api`

### Frontend
- [ ] Vendor list + detail view
- [ ] Vendor create / edit form — name, aliases, billing cycle, default category, default VAT rate
- [ ] Vendor invoice history view
- [ ] Missing invoice alerts on dashboard
- [ ] MSW handlers for vendors + dashboard

---

## Phase 4 — Dashboard + Reports + Polish

### Backend — Dashboard
- [x] `routers/dashboard.py` — monthly spend, by category, by vendor, VAT summary, MoM comparison
- [x] `test_dashboard.py` — aggregation logic

### Backend — Reports
- [x] `reporter.py` — timeframe resolution (single month / quarter / YTD / full year / custom range)
- [x] `reporter.py` — PDF generation via WeasyPrint (cover, summary, category, vendor, invoice list, unmatched, missing)
- [x] `reporter.py` — Excel generation via openpyxl (multi-sheet, filterable)
- [x] Multi-period: per-month breakdown row in all summary tables
- [x] `routers/reports.py` — timeframe + format picker, file download; `tags=["reports"]`
- [x] `test_reports.py` — timeframe aggregation, PDF + Excel output
- [x] Regenerate `openapi.json` + `pnpm generate:api`

### Frontend — Dashboard
- [ ] KPI cards — total spend ex VAT, total VAT, invoice count, match rate
- [ ] Spend by category chart (Mantine Charts)
- [ ] Spend by vendor chart
- [ ] MoM comparison chart
- [ ] VAT summary
- [ ] Missing invoice alert list

### Frontend — Reports
- [ ] Timeframe selector — single month / quarter / YTD / full year / custom range
- [ ] Custom range: `MonthPickerInput` from `@mantine/dates`
- [ ] Format picker — PDF / Excel
- [ ] Download trigger + loading state
- [ ] MSW handlers for reports

### Portal Scrapers
- [x] `scrapers/base.py` — abstract `PortalScraper` base class
- [x] `scrapers/example_supplier.py` — documented reference implementation
- [x] `routers/jobs.py` — per-supplier scrape trigger endpoint

### Polish + Deployment
- [x] Docker Compose finalised — all services, volumes, env vars
- [ ] Portainer / Raspberry Pi 5 deploy tested
- [ ] `README.md` — setup, Gmail OAuth, Drive folder, env vars, type generation, deploy
- [ ] OSS prep — licence, contributing guide

## Phase 5 — Expense Chat (RAG)

### Backend — Embeddings + Vector Store
- [x] Enable `pgvector` extension in Postgres (`CREATE EXTENSION vector`)
- [x] Alembic migration — add `embedding vector(1024)` column to `invoices` and `transactions`
- [x] `services/embeddings.py` — embed text via Voyage AI embedding model; returns `list[float]`
- [x] Embedding text format for invoices: `"{vendor} {category} {amount_incl}EUR {invoice_date} {period}"` (short, structured, no noise)
- [x] Embedding text format for transactions: `"{counterparty} {description} {amount}EUR {tx_date}"`
- [x] Background embed on invoice save (Pipeline 01 + manual upload)
- [x] Background embed on transaction confirmed match (Pipeline 02)
- [x] One-shot backfill script: embed all existing rows that have `embedding IS NULL`
- [x] `test_embeddings.py` — mock embedding API, verify text format and storage

### Backend — Chat Service
- [x] `services/chat.py` — retrieval + context builder + Claude call
  - Embed the user query
  - Vector similarity search: `ORDER BY embedding <=> query_vec LIMIT 20` across invoices + transactions
  - SQL aggregates: total spend per category, per vendor, MoM trend for current + prior 3 months (always included as grounding data)
  - Build system prompt: role, data ownership context, citation instruction ("reference invoice IDs when making specific claims")
  - Assemble user turn: question + retrieved rows (as compact markdown table) + aggregate summary
  - Stream Claude response
- [x] `services/chat.py` — persist conversation turns to `chat_messages` table (role, content, retrieved_ids, created_at)
- [x] `routers/chat.py` — `POST /chat/message` (streaming), `GET /chat/history`, `DELETE /chat/history`; `tags=["chat"]`
- [x] `test_chat.py` — mock embeddings + Claude API, verify retrieval, context assembly, history persistence
- [x] Regenerate `openapi.json` + `pnpm generate:api`

### Backend — Database
- [x] Alembic migration — `chat_messages` table: id (uuid), role (enum user/assistant), content (text), retrieved_invoice_ids (uuid[]), retrieved_tx_ids (uuid[]), created_at (timestamptz)
- [ ] pgvector index: `CREATE INDEX ON invoices USING ivfflat (embedding vector_cosine_ops)` (add after backfill, not before)

### Frontend — Chat UI
- [ ] Chat panel — message thread, streamed assistant response, input box
- [ ] Retrieved invoice chips below assistant messages — clicking opens invoice detail view
- [ ] "Clear conversation" button
- [ ] Empty state with suggested starter questions: *"What are my top 5 vendors by spend?", "What subscriptions haven't been used recently?", "What can I cut to save money?"*
- [ ] MSW handlers for chat endpoints