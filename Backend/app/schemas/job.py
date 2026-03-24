from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobStatus, JobType, TriggeredBy


class JobTrigger(BaseModel):
    job_type: JobType
    supplier: Optional[str] = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_type: JobType
    status: JobStatus
    triggered_by: TriggeredBy
    started_at: datetime
    finished_at: Optional[datetime] = None
    summary: Optional[dict[str, Any]] = None


class JobList(BaseModel):
    items: list[JobRead]
    total: int
