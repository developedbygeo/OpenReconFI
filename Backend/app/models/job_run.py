import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import JobStatus, JobType, TriggeredBy


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, name="job_type", native_enum=True),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=True),
        nullable=False,
        default=JobStatus.running,
    )
    triggered_by: Mapped[TriggeredBy] = mapped_column(
        Enum(TriggeredBy, name="triggered_by", native_enum=True),
        nullable=False,
        default=TriggeredBy.user,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
