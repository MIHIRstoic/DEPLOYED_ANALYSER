from sqlalchemy.orm import Session
from app.models.clause import Clause
from app.models.risk import Risk
from app.schemas.risk import RiskCreate


def create_risk(db: Session, clause_id: int, risk_data: RiskCreate | dict) -> Risk:
    if isinstance(risk_data, dict):
        data = risk_data
    else:
        data = risk_data.model_dump()

    risk = Risk(clause_id=clause_id, **data)
    db.add(risk)
    db.commit()
    db.refresh(risk)

    # ── FUTURE HOOK: LLM Explanations ─────────────────────────────────────
    # After a risk is identified and stored, enrich it with a plain-language
    # explanation and a concrete recommendation via an LLM.
    # Example (not implemented):
    #
    #   from app.services.llm_explainer import explain_risk
    #   explanation = await explain_risk(
    #       clause_text=risk.clause.text,
    #       risk_type=risk.risk_type,
    #       risk_level=risk.risk_level,
    #   )
    #   # explanation dict should contain:
    #   #   - reason         : str  (why this is risky, in plain language)
    #   #   - recommendation : str  (what to change / negotiate)
    #   #
    #   # Supported backends: OpenAI GPT-4o, Anthropic Claude, local Ollama.
    #   risk.reason = explanation["reason"]
    #   risk.recommendation = explanation["recommendation"]
    #   db.commit()
    #   db.refresh(risk)
    # ─────────────────────────────────────────────────────────────────────

    return risk



def get_risk(db: Session, risk_id: int) -> Risk | None:
    return db.query(Risk).filter(Risk.id == risk_id).first()


def list_risks_for_clause(db: Session, clause_id: int) -> list[Risk]:
    return db.query(Risk).filter(Risk.clause_id == clause_id).all()


def list_risks_for_contract(db: Session, contract_id: int) -> list[Risk]:
    """List all risks associated with a contract across all its clauses."""
    return (
        db.query(Risk)
        .join(Clause, Risk.clause_id == Clause.id)
        .filter(Clause.contract_id == contract_id)
        .all()
    )


def delete_risk(db: Session, risk_id: int) -> bool:
    risk = get_risk(db, risk_id)
    if risk is None:
        return False

    db.delete(risk)
    db.commit()
    return True
