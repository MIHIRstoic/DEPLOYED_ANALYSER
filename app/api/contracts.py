import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.contract import (
    create_contract,
    delete_contract,
    get_contract,
    get_contract_with_report,
    list_contracts,
    update_contract,
)
from app.schemas.contract import ContractReport, ContractResponse, ContractUpdate
from app.services.file_handler import save_temp_file, validate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


# ---------------------------------------------------------------------------
# POST /contracts/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF contract",
)
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF contract file.
    - Validates that the file is a non-empty PDF.
    - Saves the file to the local uploads/ directory.
    - Creates a Contract record in the database with status 'uploaded'.
    """
    # Will raise HTTPException(400) on invalid file
    validate_pdf(file)

    try:
        saved_path = await save_temp_file(file)
    except OSError as exc:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {exc}",
        )

    try:
        contract = create_contract(db, filename=file.filename or "upload.pdf")
        contract = update_contract(
            db, contract.id, {"filename": file.filename or "upload.pdf"}
        )

        # ── FUTURE HOOK: PDF Text Extraction / OCR ─────────────────────────
        # Once a contract is saved, kick off text extraction here.
        # Example (not implemented):
        #
        #   from app.services.pdf_extractor import extract_text
        #   raw_text = await extract_text(saved_path)
        #
        # extract_text() should use a library such as pdfplumber, PyMuPDF
        # (fitz), or an OCR engine (pytesseract / AWS Textract) for scanned
        # documents.  The extracted text is the input to the next pipeline
        # stage (clause segmentation).
        # ───────────────────────────────────────────────────────────────────

        # ── FUTURE HOOK: Clause Segmentation & Classification ──────────────
        # After text extraction, split the document into logical clauses and
        # classify each one.  Example (not implemented):
        #
        #   from app.services.clause_segmenter import segment_and_classify
        #   clauses = await segment_and_classify(raw_text, contract.id)
        #   # Each item in `clauses` should contain:
        #   #   - text          : str      (the clause body)
        #   #   - clause_type   : str      (e.g. "Indemnity", "Confidentiality")
        #   #   - clause_number : str      (e.g. "3.1")
        #   #   - page_number   : int
        #   #   - confidence    : float    (model confidence score 0-1)
        #   for c in clauses:
        #       crud.clause.create_clause(db, contract_id=contract.id,
        #                                 clause_data=ClauseCreate(**c))
        #
        # This can be done synchronously here or dispatched to a background
        # task queue (e.g. Celery, ARQ) for large documents.
        # ───────────────────────────────────────────────────────────────────

        return contract

    except IntegrityError as exc:
        db.rollback()
        logger.exception("Database integrity error on contract creation")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. The contract could not be created.",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unexpected database error on contract creation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )


# ---------------------------------------------------------------------------
# GET /contracts
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=List[ContractResponse],
    summary="List all contracts",
)
def list_all_contracts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    db: Session = Depends(get_db),
):
    """Return a paginated list of all contracts."""
    try:
        return list_contracts(db, skip=skip, limit=limit)
    except SQLAlchemyError:
        logger.exception("Database error while listing contracts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}/report
# ---------------------------------------------------------------------------
@router.get(
    "/{contract_id}/report",
    response_model=ContractReport,
    summary="Get an aggregated contract report",
)
def get_contract_report(
    contract_id: int,
    db: Session = Depends(get_db),
):
    """
    Return a full contract report with nested clauses and risks.
    Uses eager loading (selectinload) to avoid N+1 queries.
    """
    try:
        contract = get_contract_with_report(db, contract_id)
    except SQLAlchemyError:
        logger.exception("DB error fetching report for contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found.",
        )
    return contract


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Get a contract by ID",
)
def get_contract_by_id(
    contract_id: int,
    db: Session = Depends(get_db),
):
    """Fetch a single contract by its database ID. Returns 404 if not found."""
    try:
        contract = get_contract(db, contract_id)
    except SQLAlchemyError:
        logger.exception("Database error fetching contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found.",
        )
    return contract


# ---------------------------------------------------------------------------
# PATCH /contracts/{contract_id}
# ---------------------------------------------------------------------------
@router.patch(
    "/{contract_id}",
    response_model=ContractResponse,
    summary="Update a contract",
)
def patch_contract(
    contract_id: int,
    updates: ContractUpdate,
    db: Session = Depends(get_db),
):
    """
    Partially update a contract's metadata (status, overall_score, contract_type, filename).
    Returns 404 if the contract does not exist.
    """
    try:
        updated = update_contract(db, contract_id, updates)
    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error updating contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update contract due to a database integrity error.",
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error updating contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found.",
        )
    return updated


# ---------------------------------------------------------------------------
# DELETE /contracts/{contract_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contract",
)
def remove_contract(
    contract_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a contract and all its associated clauses and risks (ON DELETE CASCADE).
    Returns 204 No Content on success, 404 if not found.
    """
    try:
        deleted = delete_contract(db, contract_id)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error deleting contract %d", contract_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected database error occurred.",
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with id={contract_id} not found.",
        )
