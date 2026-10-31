import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.clause import (
    create_clause,
    delete_clause,
    get_clause,
    list_clauses_for_contract,
)
from app.crud.contract import get_contract
from app.schemas.clause import ClauseCreate, ClauseResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routes nested under contracts: /contracts/{contract_id}/clauses
# ---------------------------------------------------------------------------
contracts_router = APIRouter(prefix="/contracts", tags=["Clauses"])

# ---------------------------------------------------------------------------
# Routes for individual clauses: /clauses/{clause_id}
# ---------------------------------------------------------------------------
clauses_router = APIRouter(prefix="/clauses", tags=["Clauses"])


# ---------------------------------------------------------------------------
# POST /contracts/{contract_id}/clauses
# ---------------------------------------------------------------------------
@contracts_router.post(
    "/{contract_id}/clauses",
    response_model=ClauseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a clause under a contract",
)
def create_clause_for_contract(
    contract_id: int,
    clause_data: ClauseCreate,
    db: Session = Depends(get_db),
):
    """
    Create and attach a clause to the specified contract.
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
        return create_clause(db, contract_id=contract_id, clause_data=clause_data)
    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error creating clause for contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create clause due to a database integrity error.",
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("DB error creating clause for contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}/clauses
# ---------------------------------------------------------------------------
@contracts_router.get(
    "/{contract_id}/clauses",
    response_model=List[ClauseResponse],
    summary="List all clauses for a contract",
)
def list_clauses(
    contract_id: int,
    db: Session = Depends(get_db),
):
    """
    Return all clauses belonging to the specified contract.
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
        return list_clauses_for_contract(db, contract_id)
    except SQLAlchemyError:
        logger.exception("DB error listing clauses for contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )


# ---------------------------------------------------------------------------
# GET /clauses/{clause_id}
# ---------------------------------------------------------------------------
@clauses_router.get(
    "/{clause_id}",
    response_model=ClauseResponse,
    summary="Get a clause by ID",
)
def get_clause_by_id(
    clause_id: int,
    db: Session = Depends(get_db),
):
    """Fetch a single clause by its ID. Returns 404 if not found."""
    try:
        clause = get_clause(db, clause_id)
    except SQLAlchemyError:
        logger.exception("DB error fetching clause %d", clause_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if clause is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause with id={clause_id} not found.",
        )
    return clause


# ---------------------------------------------------------------------------
# DELETE /clauses/{clause_id}
# ---------------------------------------------------------------------------
@clauses_router.delete(
    "/{clause_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a clause",
)
def remove_clause(
    clause_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a clause and all its associated risks (ON DELETE CASCADE).
    Returns 204 No Content on success, 404 if not found.
    """
    try:
        deleted = delete_clause(db, clause_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("DB error deleting clause %d", clause_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause with id={clause_id} not found.",
        )
