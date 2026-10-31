import pytest
from app.core.database import SessionLocal
from app.schemas.contract import ContractUpdate
from app.schemas.clause import ClauseCreate
from app.schemas.risk import RiskCreate
from app.crud.contract import (
    create_contract,
    get_contract,
    list_contracts,
    update_contract,
    delete_contract,
)
from app.crud.clause import (
    create_clause,
    get_clause,
    list_clauses_for_contract,
    delete_clause,
)
from app.crud.risk import (
    create_risk,
    get_risk,
    list_risks_for_clause,
    list_risks_for_contract,
    delete_risk,
)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_contract_crud(db_session):
    # 1. Create contract
    contract = create_contract(db_session, filename="test_agreement.pdf")
    assert contract.id is not None
    assert contract.filename == "test_agreement.pdf"
    assert contract.status == "uploaded"

    contract_id = contract.id

    # 2. Get contract
    fetched = get_contract(db_session, contract_id)
    assert fetched is not None
    assert fetched.id == contract_id

    # Non-existent
    assert get_contract(db_session, -999) is None

    # 3. List contracts
    contracts = list_contracts(db_session, skip=0, limit=10)
    assert any(c.id == contract_id for c in contracts)

    # 4. Update contract with schema
    update_data = ContractUpdate(status="analyzed", overall_score=85.5)
    updated = update_contract(db_session, contract_id, update_data)
    assert updated is not None
    assert updated.status == "analyzed"
    assert updated.overall_score == 85.5

    # Update contract with dict
    updated_dict = update_contract(db_session, contract_id, {"contract_type": "NDA"})
    assert updated_dict is not None
    assert updated_dict.contract_type == "NDA"

    # Non-existent update returns None
    assert update_contract(db_session, -999, update_data) is None

    # 5. Delete contract
    assert delete_contract(db_session, contract_id) is True
    assert get_contract(db_session, contract_id) is None
    assert delete_contract(db_session, contract_id) is False


def test_clause_crud(db_session):
    contract = create_contract(db_session, filename="clause_test.pdf")
    contract_id = contract.id

    try:
        clause_data = ClauseCreate(
            clause_number="1.1",
            clause_type="Confidentiality",
            text="Recipient agrees to keep information confidential.",
            page_number=1,
            confidence=0.98,
        )
        clause = create_clause(db_session, contract_id, clause_data)
        assert clause.id is not None
        assert clause.contract_id == contract_id
        assert clause.clause_number == "1.1"

        clause_id = clause.id

        # Get clause
        fetched = get_clause(db_session, clause_id)
        assert fetched is not None
        assert fetched.id == clause_id
        assert get_clause(db_session, -999) is None

        # List clauses for contract
        clauses = list_clauses_for_contract(db_session, contract_id)
        assert len(clauses) >= 1
        assert any(c.id == clause_id for c in clauses)

        # Delete clause
        assert delete_clause(db_session, clause_id) is True
        assert get_clause(db_session, clause_id) is None
        assert delete_clause(db_session, clause_id) is False

    finally:
        delete_contract(db_session, contract_id)


def test_risk_crud(db_session):
    contract = create_contract(db_session, filename="risk_test.pdf")
    contract_id = contract.id

    try:
        clause = create_clause(
            db_session,
            contract_id,
            ClauseCreate(
                clause_number="2.1",
                clause_type="Indemnity",
                text="Party A indemnifies Party B without limitation.",
                page_number=3,
                confidence=0.95,
            ),
        )
        clause_id = clause.id

        risk_data = RiskCreate(
            risk_type="Unlimited Liability",
            risk_level="HIGH",
            reason="Uncapped indemnification exposes party to excessive financial risk.",
            evidence="without limitation",
            recommendation="Introduce a liability cap equal to total contract fees.",
        )
        risk = create_risk(db_session, clause_id, risk_data)
        assert risk.id is not None
        assert risk.clause_id == clause_id
        assert risk.risk_level == "HIGH"

        risk_id = risk.id

        # Get risk
        fetched = get_risk(db_session, risk_id)
        assert fetched is not None
        assert fetched.id == risk_id
        assert get_risk(db_session, -999) is None

        # List risks for clause
        clause_risks = list_risks_for_clause(db_session, clause_id)
        assert any(r.id == risk_id for r in clause_risks)

        # List risks for contract (join across clauses)
        contract_risks = list_risks_for_contract(db_session, contract_id)
        assert any(r.id == risk_id for r in contract_risks)

        # Delete risk
        assert delete_risk(db_session, risk_id) is True
        assert get_risk(db_session, risk_id) is None
        assert delete_risk(db_session, risk_id) is False

    finally:
        delete_contract(db_session, contract_id)
