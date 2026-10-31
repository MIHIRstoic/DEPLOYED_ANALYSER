from pydantic import BaseModel, ConfigDict


class RiskBase(BaseModel):
    risk_type: str | None = None
    risk_level: str | None = None
    reason: str | None = None
    evidence: str | None = None
    recommendation: str | None = None


class RiskCreate(RiskBase):
    pass


class RiskUpdate(BaseModel):
    risk_type: str | None = None
    risk_level: str | None = None
    reason: str | None = None
    evidence: str | None = None
    recommendation: str | None = None


class RiskResponse(RiskBase):
    id: int
    clause_id: int

    model_config = ConfigDict(from_attributes=True)
