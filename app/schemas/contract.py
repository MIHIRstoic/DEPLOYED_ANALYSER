from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ContractBase(BaseModel):
    filename: str
    contract_type: str | None = None
    status: str = "uploaded"
    overall_score: float | None = None


class ContractCreate(BaseModel):
    filename: str
    contract_type: str | None = None


class ContractUpdate(BaseModel):
    filename: str | None = None
    contract_type: str | None = None
    status: str | None = None
    overall_score: float | None = None


class ContractResponse(ContractBase):
    id: int
    upload_date: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Nested report schemas (contract → clauses[] → risks[])
# ---------------------------------------------------------------------------
from app.schemas.risk import RiskResponse  # noqa: E402
from app.schemas.clause import ClauseResponse  # noqa: E402


class ClauseWithRisks(ClauseResponse):
    """A clause together with all its associated risks."""
    risks: list[RiskResponse] = []


class ContractReport(ContractResponse):
    """Full contract report: contract fields + nested clauses, each with nested risks."""
    clauses: list[ClauseWithRisks] = []
