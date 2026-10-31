import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.clause import get_clause
from app.crud.contract import get_contract
from app.crud.risk import (
    create_risk,
    delete_risk,
    get_risk,
    list_risks_for_clause,
    list_risks_for_contract,
)
from app.schemas.risk import RiskCreate, RiskResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routes nested under clauses: /clauses/{clause_id}/risks
# Routes nested under contracts: /contracts/{contract_id}/risks
# ---------------------------------------------------------------------------
clauses_router = APIRouter(prefix="/clauses", tags=["Risks"])
contracts_router = APIRouter(prefix="/contracts", tags=["Risks"])
risks_router = APIRouter(prefix="/risks", tags=["Risks"])


# ---------------------------------------------------------------------------
# POST /clauses/{clause_id}/risks
# ---------------------------------------------------------------------------
@clauses_router.post(
    "/{clause_id}/risks",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a risk under a clause",
)
def create_risk_for_clause(
    clause_id: int,
    risk_data: RiskCreate,
    db: Session = Depends(get_db),
):
    """
    Create and attach a risk to the specified clause.
    Returns 404 if the clause does not exist.
    """
    try:
        clause = get_clause(db, clause_id)
    except SQLAlchemyError:
        logger.exception("DB error checking clause %d", clause_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if clause is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause with id={clause_id} not found.",
        )

    try:
        return create_risk(db, clause_id=clause_id, risk_data=risk_data)
    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error creating risk for clause %d", clause_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create risk due to a database integrity error.",
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("DB error creating risk for clause %d", clause_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )


# ---------------------------------------------------------------------------
# GET /clauses/{clause_id}/risks
# ---------------------------------------------------------------------------
@clauses_router.get(
    "/{clause_id}/risks",
    response_model=List[RiskResponse],
    summary="List risks for a clause",
)
def list_risks_by_clause(
    clause_id: int,
    db: Session = Depends(get_db),
):
    """
    Return all risks for the given clause.
    Returns 404 if the clause does not exist.
    """
    try:
        clause = get_clause(db, clause_id)
    except SQLAlchemyError:
        logger.exception("DB error checking clause %d", clause_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if clause is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause with id={clause_id} not found.",
        )

    try:
        return list_risks_for_clause(db, clause_id)
    except SQLAlchemyError:
        logger.exception("DB error listing risks for clause %d", clause_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}/risks
# ---------------------------------------------------------------------------
@contracts_router.get(
    "/{contract_id}/risks",
    response_model=List[RiskResponse],
    summary="List all risks across a contract",
)
def list_risks_by_contract(
    contract_id: int,
    db: Session = Depends(get_db),
):
    """
    Return all risks across all clauses belonging to the specified contract.
    Returns 404 if the contract does not exist.
    """
    try:
        contract = get_contract(db, contract_id)
    except SQLAlchemyError:
        logger.exception("DB error checking contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found.",
        )

    try:
        return list_risks_for_contract(db, contract_id)
    except SQLAlchemyError:
        logger.exception("DB error listing risks for contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )


# ---------------------------------------------------------------------------
# DELETE /risks/{risk_id}
# ---------------------------------------------------------------------------
@risks_router.delete(
    "/{risk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a risk",
)
def remove_risk(
    risk_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a single risk record.
    Returns 204 No Content on success, 404 if not found.
    """
    try:
        deleted = delete_risk(db, risk_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("DB error deleting risk %d", risk_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk with id={risk_id} not found.",
        )
