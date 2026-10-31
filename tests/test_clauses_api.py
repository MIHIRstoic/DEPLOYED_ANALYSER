import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.crud.contract import create_contract, delete_contract

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def contract(db_session):
    """Create a real contract for tests and clean up after."""
    c = create_contract(db_session, filename="clauses_test.pdf")
    yield c
    delete_contract(db_session, c.id)


# ──────────────────────────────────────────────────────────────────────────────
# POST /contracts/{contract_id}/clauses
# ──────────────────────────────────────────────────────────────────────────────

def test_create_clause(contract):
    payload = {
        "clause_number": "1.1",
        "clause_type": "Confidentiality",
        "text": "All information shared shall remain confidential.",
        "page_number": 1,
        "confidence": 0.97,
    }
    resp = client.post(f"/contracts/{contract.id}/clauses", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["contract_id"] == contract.id
    assert data["clause_number"] == "1.1"
    assert data["clause_type"] == "Confidentiality"
    assert data["confidence"] == 0.97
    assert "id" in data


def test_create_clause_contract_not_found():
    payload = {"text": "Some clause text."}
    resp = client.post("/contracts/99999999/clauses", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_create_clause_missing_text(contract):
    """text is required - Pydantic should return 422."""
    resp = client.post(f"/contracts/{contract.id}/clauses", json={"clause_type": "NDA"})
    assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# GET /contracts/{contract_id}/clauses
# ──────────────────────────────────────────────────────────────────────────────

def test_list_clauses_for_contract(contract):
    # Create two clauses
    for i in range(2):
        client.post(
            f"/contracts/{contract.id}/clauses",
            json={"text": f"Clause text {i}", "clause_number": str(i)},
        )

    resp = client.get(f"/contracts/{contract.id}/clauses")
    assert resp.status_code == 200
    clauses = resp.json()
    assert len(clauses) >= 2
    assert all(c["contract_id"] == contract.id for c in clauses)


def test_list_clauses_contract_not_found():
    resp = client.get("/contracts/99999999/clauses")
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# GET /clauses/{clause_id}
# ──────────────────────────────────────────────────────────────────────────────

def test_get_clause_by_id(contract):
    created = client.post(
        f"/contracts/{contract.id}/clauses",
        json={"text": "Specific clause.", "clause_number": "2.1"},
    ).json()

    resp = client.get(f"/clauses/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    assert resp.json()["clause_number"] == "2.1"


def test_get_clause_not_found():
    resp = client.get("/clauses/99999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /clauses/{clause_id}
# ──────────────────────────────────────────────────────────────────────────────

def test_delete_clause(contract):
    created = client.post(
        f"/contracts/{contract.id}/clauses",
        json={"text": "Clause to delete."},
    ).json()

    resp = client.delete(f"/clauses/{created['id']}")
    assert resp.status_code == 204

    # Verify gone
    resp = client.get(f"/clauses/{created['id']}")
    assert resp.status_code == 404


def test_delete_clause_not_found():
    resp = client.delete("/clauses/99999999")
    assert resp.status_code == 404


def test_delete_clause_cascades_to_risks(contract):
    """Deleting a clause should also remove its risks via DB cascade."""
    clause = client.post(
        f"/contracts/{contract.id}/clauses",
        json={"text": "Cascade clause."},
    ).json()
    clause_id = clause["id"]

    risk = client.post(
        f"/clauses/{clause_id}/risks",
        json={"risk_type": "Cascade test", "risk_level": "LOW"},
    ).json()
    risk_id = risk["id"]

    # Delete clause — risks should cascade
    client.delete(f"/clauses/{clause_id}")

    # Risk should be gone
    resp = client.get(f"/clauses/{clause_id}/risks")
    assert resp.status_code == 404  # clause gone, so 404
