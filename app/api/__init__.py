from app.api.contracts import router as contracts_router
from app.api.clauses import contracts_router as clauses_contracts_router
from app.api.clauses import clauses_router as clauses_router
from app.api.risks import clauses_router as risks_clauses_router
from app.api.risks import contracts_router as risks_contracts_router
from app.api.risks import risks_router

__all__ = [
    "contracts_router",
    "clauses_contracts_router",
    "clauses_router",
    "risks_clauses_router",
    "risks_contracts_router",
    "risks_router",
]
