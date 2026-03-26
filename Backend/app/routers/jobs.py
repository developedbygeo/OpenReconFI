import asyncio
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.enums import JobStatus, JobType
from app.models.job_run import JobRun
from app.schemas.job import JobList, JobRead, JobTrigger

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobList)
async def list_jobs(
    job_type: Optional[JobType] = Query(None),
    status: Optional[JobStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JobList:
    query = select(JobRun)
    count_query = select(func.count(JobRun.id))

    if job_type:
        query = query.where(JobRun.job_type == job_type)
        count_query = count_query.where(JobRun.job_type == job_type)
    if status:
        query = query.where(JobRun.status == status)
        count_query = count_query.where(JobRun.status == status)

    query = query.order_by(JobRun.started_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return JobList(
        items=[JobRead.model_validate(j) for j in jobs],
        total=total,
    )


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    result = await db.execute(select(JobRun).where(JobRun.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)


@router.post("", response_model=JobRead, status_code=201)
async def trigger_job(
    body: JobTrigger,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    """Trigger a new job (gmail_sync, portal_scrape, reconcile)."""
    job = JobRun(job_type=body.job_type, status=JobStatus.running)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    if body.job_type == JobType.gmail_sync:
        background_tasks.add_task(_run_gmail_sync, job.id)
    elif body.job_type == JobType.portal_scrape:
        background_tasks.add_task(_run_portal_scrape, job.id, body.supplier)

    return JobRead.model_validate(job)


async def _run_portal_scrape(job_id: UUID, supplier: str | None) -> None:
    """Background task: runs a portal scraper for the given supplier."""
    from app.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Supplier-specific scraper lookup would go here.
            # For now, mark as failed if no supplier specified.
            if not supplier:
                raise ValueError("supplier is required for portal_scrape jobs")

            # Placeholder: import and run the supplier's scraper
            raise NotImplementedError(f"Scraper for '{supplier}' is not yet configured")
        except Exception as exc:
            result = await db.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = JobStatus.failed
            job.summary = {"error": str(exc)}
        finally:
            from datetime import datetime, timezone

            job.finished_at = datetime.now(timezone.utc)
            await db.commit()


async def _run_gmail_sync(job_id: UUID) -> None:
    """Background task: runs the Gmail collection pipeline."""
    from app.db import AsyncSessionLocal
    from app.services.collector import run_collection

    async with AsyncSessionLocal() as db:
        try:
            summary = await run_collection(db)
            result = await db.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = JobStatus.done
            job.summary = summary
        except Exception as exc:
            result = await db.execute(select(JobRun).where(JobRun.id == job_id))
            job = result.scalar_one()
            job.status = JobStatus.failed
            job.summary = {"error": str(exc)}
        finally:
            from datetime import datetime, timezone

            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
