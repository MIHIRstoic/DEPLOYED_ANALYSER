from fastapi import FastAPI
from app.core.config import settings
from app.api.contracts import router as contracts_router
from app.api.clauses import contracts_router as clauses_on_contracts_router
from app.api.clauses import clauses_router
from app.api.risks import clauses_router as risks_on_clauses_router
from app.api.risks import contracts_router as risks_on_contracts_router
from app.api.risks import risks_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI-Based Legal Contract Analysis and Risk Detection System",
    version="0.1.0",
)

# ── Contracts ───────────────────────────────────────────────────────────────
app.include_router(contracts_router)

# ── Clauses ─────────────────────────────────────────────────────────────────
# POST /contracts/{contract_id}/clauses
# GET  /contracts/{contract_id}/clauses
app.include_router(clauses_on_contracts_router)
# GET    /clauses/{clause_id}
# DELETE /clauses/{clause_id}
app.include_router(clauses_router)

# ── Risks ────────────────────────────────────────────────────────────────────
# POST /clauses/{clause_id}/risks
# GET  /clauses/{clause_id}/risks
app.include_router(risks_on_clauses_router)
# GET /contracts/{contract_id}/risks
app.include_router(risks_on_contracts_router)
# DELETE /risks/{risk_id}
app.include_router(risks_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
