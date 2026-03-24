from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, dashboard, invoices, jobs, reconciliation, reports, vendors

app = FastAPI(
    title="Matchbook API",
    version="0.1.0",
    description="Self-hosted agency finance ops — invoice collection, reconciliation, reporting.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices.router)
app.include_router(jobs.router)
app.include_router(reconciliation.router)
app.include_router(vendors.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(chat.router)


@app.get("/health", response_model=dict, tags=["system"])
async def health() -> dict:
    return {"status": "ok"}
