from sqlalchemy.orm import Session, selectinload
from app.models.contract import Contract
from app.models.clause import Clause
from app.schemas.contract import ContractUpdate


def get_contract_with_report(db: Session, contract_id: int) -> Contract | None:
    """
    Eagerly load a contract together with its clauses and each clause's risks.
    Uses selectinload to avoid N+1 queries.
    Returns None if the contract does not exist.
    """
    return (
        db.query(Contract)
        .options(
            selectinload(Contract.clauses).selectinload(Clause.risks)
        )
        .filter(Contract.id == contract_id)
        .first()
    )


def create_contract(db: Session, filename: str) -> Contract:
    contract = Contract(filename=filename)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def get_contract(db: Session, contract_id: int) -> Contract | None:
    return db.query(Contract).filter(Contract.id == contract_id).first()


def list_contracts(db: Session, skip: int = 0, limit: int = 100) -> list[Contract]:
    return db.query(Contract).offset(skip).limit(limit).all()


def update_contract(
    db: Session, contract_id: int, updates: ContractUpdate | dict
) -> Contract | None:
    contract = get_contract(db, contract_id)
    if contract is None:
        return None

    if isinstance(updates, dict):
        update_data = updates
    else:
        update_data = updates.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(contract, field, value)

    db.commit()
    db.refresh(contract)
    return contract


def delete_contract(db: Session, contract_id: int) -> bool:
    contract = get_contract(db, contract_id)
    if contract is None:
        return False

    db.delete(contract)
    db.commit()
    return True
