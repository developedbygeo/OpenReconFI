from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    color: str


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    color: str
