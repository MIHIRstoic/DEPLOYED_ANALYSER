from sqlalchemy.orm import Session
from app.models.clause import Clause
from app.schemas.clause import ClauseCreate


def create_clause(
    db: Session, contract_id: int, clause_data: ClauseCreate | dict
) -> Clause:
    if isinstance(clause_data, dict):
        data = clause_data
    else:
        data = clause_data.model_dump()

    clause = Clause(contract_id=contract_id, **data)
    db.add(clause)
    db.commit()
    db.refresh(clause)

    # ── FUTURE HOOK: Risk Detection Engine ────────────────────────────────
    # Once a clause is persisted, analyse it for legal risks.
    # Example (not implemented):
    #
    #   from app.services.risk_engine import detect_risks
    #   detected = detect_risks(clause.text, clause.clause_type)
    #   # detect_risks() returns a list of dicts with keys:
    #   #   - risk_type    : str   (e.g. "Unlimited Liability")
    #   #   - risk_level   : str   (e.g. "HIGH" | "MEDIUM" | "LOW")
    #   #   - evidence     : str   (verbatim excerpt that triggered the flag)
    #   # The risk engine can be rule-based, ML-based, or LLM-based.
    #   for r in detected:
    #       create_risk(db, clause_id=clause.id,
    #                   risk_data=RiskCreate(**r))
    # ─────────────────────────────────────────────────────────────────────

    return clause



def get_clause(db: Session, clause_id: int) -> Clause | None:
    return db.query(Clause).filter(Clause.id == clause_id).first()


def list_clauses_for_contract(db: Session, contract_id: int) -> list[Clause]:
    return db.query(Clause).filter(Clause.contract_id == contract_id).all()


def delete_clause(db: Session, clause_id: int) -> bool:
    clause = get_clause(db, clause_id)
    if clause is None:
        return False

    db.delete(clause)
    db.commit()
    return True
