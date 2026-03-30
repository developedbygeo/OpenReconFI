# OpenReconFi — Frontend

React SPA for OpenReconFi, built with TypeScript, Vite, Mantine UI, and Redux Toolkit.

## Prerequisites

- Node.js 18+
- [pnpm](https://pnpm.io/)
- Backend running at `http://localhost:8000` (see [Backend README](../Backend/README.md))

## Quick Start

```bash
pnpm install
pnpm run dev
```

App is live at **http://localhost:5173**. API requests to `/api/*` are proxied to the backend.

## Scripts

| Command | Description |
|---|---|
| `pnpm run dev` | Start Vite dev server with HMR |
| `pnpm run build` | Type-check with `tsc` then build for production |
| `pnpm run preview` | Preview the production build locally |
| `pnpm run lint` | Run ESLint |
| `pnpm run generate:api` | Regenerate API client from `../openapi.json` via Orval |

## Tech Stack

- **React 19** + TypeScript 5.9
- **Vite 8** — build tool with HMR
- **Mantine v8** — UI components (core, charts, forms, dropzone, dates, notifications)
- **Redux Toolkit** — RTK Query for server state, cache invalidation via tags
- **React Router v6** — client-side routing
- **Orval** — generates TypeScript types + Zod schemas from the backend OpenAPI spec
- **Tabler Icons** — icon library
- **react-markdown** + remark-gfm — renders LLM chat responses

## Feature Modules

Each feature lives in `src/features/` with its own pages, components, hooks, and skeletons:

| Feature | Route(s) | Description |
|---|---|---|
| **Dashboard** | `/dashboard` | KPI cards, spend charts, VAT/tax summaries, MoM comparison, missing invoice alerts |
| **Invoices** | `/invoices`, `/invoices/:id` | Invoice list with pagination and filters, detail view, inline category assignment |
| **Collection** | `/collection` | Trigger Gmail sync, track job history with polling |
| **Reconciliation** | `/reconciliation/*` | Statement upload, match review (confirm/reject/reassign), reconciliation overview, manual matching |
| **Vendors** | `/vendors/*` | Vendor CRUD with billing cycles, aliases, and invoice history |
| **Reports** | `/reports` | Generate PDF/Excel reports with flexible timeframes, preview before download |
| **Chat** | `/chat` | AI expense chat with streaming, starter questions, follow-up suggestions, markdown rendering |

## Project Structure

```
src/
├── api/                    # Generated API client (Orval output)
│   └── types/              # Generated TypeScript types
├── components/             # Shared components (AppShell, TableSkeleton)
├── features/               # Feature modules
│   ├── dashboard/
│   │   ├── index.tsx
│   │   ├── useDashboardData.ts
│   │   └── _components/
│   ├── invoices/
│   │   └── _components/
│   ├── chat/
│   │   ├── _components/
│   │   └── _hooks/
│   └── ...
├── store/                  # Redux + RTK Query
│   ├── api.ts              # Base API (tags, baseQuery)
│   ├── store.ts            # Store configuration
│   ├── hooks.ts            # Typed Redux hooks
│   ├── invoicesApi.ts      # Invoice endpoints
│   ├── vendorsApi.ts       # Vendor endpoints
│   ├── reconciliationApi.ts
│   ├── dashboardApi.ts
│   ├── chatApi.ts
│   ├── jobsApi.ts
│   ├── reportsApi.ts
│   └── categoriesApi.ts
├── test/                   # Vitest + MSW setup
│   └── mocks/              # Mock handlers and data
├── utils/                  # Shared utilities (formatMoney, etc.)
├── App.tsx                 # Route definitions
└── main.tsx                # Entry point (Redux provider, Mantine theme)
```

## API Client Generation

The frontend consumes the backend's OpenAPI spec via [Orval](https://orval.dev/):

```bash
# 1. Export the spec from the backend (no server needed)
cd ../Backend && python export_schema.py

# 2. Regenerate the client
cd ../Frontend && pnpm run generate:api
```

This generates TypeScript types and Zod validation schemas in `src/api/`. The RTK Query slices in `src/store/` reference these types directly.

## State Management

All server state is managed through **RTK Query** with domain-specific API slices (`src/store/*Api.ts`). Each slice uses `injectEndpoints` into a shared base API, so cache invalidation works across domains (e.g., confirming a match invalidates invoices, transactions, and matches).

No additional Redux state slices — RTK Query handles caching, refetching on focus/reconnect, and optimistic updates.

## Testing

Testing infrastructure is set up with Vitest, Testing Library, and MSW:

```bash
pnpm run test
```

- **Vitest** — test runner with jsdom environment
- **@testing-library/react** — component testing
- **MSW** — mocks API responses at the network level
- Mock handlers and data in `src/test/mocks/`

## Dev Server Proxy

Vite proxies `/api/*` requests to the backend (`http://localhost:8000`), stripping the `/api` prefix:

```
Frontend /api/invoices → Backend /invoices
```

No CORS issues in development — the proxy handles it transparently.
