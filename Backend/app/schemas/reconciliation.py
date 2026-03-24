from pydantic import BaseModel


class StatementUploadResponse(BaseModel):
    transactions_parsed: int
    period: str


class MatchTriggerRequest(BaseModel):
    period: str


class MatchTriggerResponse(BaseModel):
    matches_suggested: int
    period: str
