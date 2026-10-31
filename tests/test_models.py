from app.core.database import Base
from app.models.contract import Contract
from app.models.clause import Clause
from app.models.risk import Risk


def test_models_metadata_registration():
    table_names = Base.metadata.tables.keys()
    assert "contracts" in table_names
    assert "clauses" in table_names
    assert "risks" in table_names


def test_contract_model_columns():
    table = Base.metadata.tables["contracts"]
    columns = {c.name: c for c in table.columns}

    assert "id" in columns and columns["id"].primary_key
    assert "filename" in columns and not columns["filename"].nullable
    assert "contract_type" in columns and columns["contract_type"].nullable
    assert "upload_date" in columns and not columns["upload_date"].nullable
    assert "status" in columns and not columns["status"].nullable
    assert "overall_score" in columns and columns["overall_score"].nullable


def test_clause_model_columns():
    table = Base.metadata.tables["clauses"]
    columns = {c.name: c for c in table.columns}

    assert "id" in columns and columns["id"].primary_key
    assert "contract_id" in columns and not columns["contract_id"].nullable
    assert "clause_number" in columns and columns["clause_number"].nullable
    assert "clause_type" in columns and columns["clause_type"].nullable
    assert "text" in columns and not columns["text"].nullable
    assert "page_number" in columns and columns["page_number"].nullable
    assert "confidence" in columns and columns["confidence"].nullable

    # Check foreign key
    fks = list(columns["contract_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "contracts.id"
    assert fks[0].ondelete == "CASCADE"


def test_risk_model_columns():
    table = Base.metadata.tables["risks"]
    columns = {c.name: c for c in table.columns}

    assert "id" in columns and columns["id"].primary_key
    assert "clause_id" in columns and not columns["clause_id"].nullable
    assert "risk_type" in columns and columns["risk_type"].nullable
    assert "risk_level" in columns and columns["risk_level"].nullable
    assert "reason" in columns and columns["reason"].nullable
    assert "evidence" in columns and columns["evidence"].nullable
    assert "recommendation" in columns and columns["recommendation"].nullable

    # Check foreign key
    fks = list(columns["clause_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "clauses.id"
    assert fks[0].ondelete == "CASCADE"


def test_model_relationships():
    # Verify relationships are configured
    assert hasattr(Contract, "clauses")
    assert hasattr(Clause, "contract")
    assert hasattr(Clause, "risks")
    assert hasattr(Risk, "clause")
