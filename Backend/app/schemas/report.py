from typing import Optional

from pydantic import BaseModel

from app.models.enums import ReportFormat, TimeframeType


class ReportRequest(BaseModel):
    timeframe: TimeframeType
    format: ReportFormat
    variant: str = "full"  # "full" or "summary"
    period: Optional[str] = None
    quarter: Optional[int] = None
    year: Optional[int] = None
    from_period: Optional[str] = None
    to_period: Optional[str] = None


class ReportMeta(BaseModel):
    timeframe_label: str
    periods: list[str]
    format: ReportFormat
    filename: str
