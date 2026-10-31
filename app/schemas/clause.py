from pydantic import BaseModel, ConfigDict


class ClauseBase(BaseModel):
    clause_number: str | None = None
    clause_type: str | None = None
    text: str
    page_number: int | None = None
    confidence: float | None = None


class ClauseCreate(ClauseBase):
    pass


class ClauseUpdate(BaseModel):
    clause_number: str | None = None
    clause_type: str | None = None
    text: str | None = None
    page_number: int | None = None
    confidence: float | None = None


class ClauseResponse(ClauseBase):
    id: int
    contract_id: int

    model_config = ConfigDict(from_attributes=True)
