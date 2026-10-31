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
def contract_with_clause(db_session):
    """Create a contract with one clause and clean up after."""
    c = create_contract(db_session, filename="risks_test.pdf")
    clause_resp = client.post(
        f"/contracts/{c.id}/clauses",
        json={
            "text": "Party A indemnifies Party B without cap.",
            "clause_number": "3.1",
            "clause_type": "Indemnity",
        },
    )
    clause = clause_resp.json()
    yield {"contract": c, "clause": clause}
    delete_contract(db_session, c.id)


# ──────────────────────────────────────────────────────────────────────────────
# POST /clauses/{clause_id}/risks
# ──────────────────────────────────────────────────────────────────────────────

def test_create_risk(contract_with_clause):
    clause_id = contract_with_clause["clause"]["id"]
    payload = {
        "risk_type": "Unlimited Liability",
        "risk_level": "HIGH",
        "reason": "No cap on indemnification.",
        "evidence": "without cap",
        "recommendation": "Add a liability cap.",
    }
    resp = client.post(f"/clauses/{clause_id}/risks", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["clause_id"] == clause_id
    assert data["risk_type"] == "Unlimited Liability"
    assert data["risk_level"] == "HIGH"
    assert "id" in data


def test_create_risk_clause_not_found():
    resp = client.post("/clauses/99999999/risks", json={"risk_type": "X"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# GET /clauses/{clause_id}/risks
# ──────────────────────────────────────────────────────────────────────────────

def test_list_risks_for_clause(contract_with_clause):
    clause_id = contract_with_clause["clause"]["id"]
    # Create two risks
    for i, level in enumerate(["LOW", "MEDIUM"]):
        client.post(
            f"/clauses/{clause_id}/risks",
            json={"risk_type": f"Risk {i}", "risk_level": level},
        )

    resp = client.get(f"/clauses/{clause_id}/risks")
    assert resp.status_code == 200
    risks = resp.json()
    assert len(risks) >= 2
    assert all(r["clause_id"] == clause_id for r in risks)


def test_list_risks_clause_not_found():
    resp = client.get("/clauses/99999999/risks")
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# GET /contracts/{contract_id}/risks
# ──────────────────────────────────────────────────────────────────────────────

def test_list_risks_for_contract(contract_with_clause):
    contract_id = contract_with_clause["contract"].id
    clause_id = contract_with_clause["clause"]["id"]

    # Add a risk to the clause
    client.post(
        f"/clauses/{clause_id}/risks",
        json={"risk_type": "Contract-level risk", "risk_level": "HIGH"},
    )

    resp = client.get(f"/contracts/{contract_id}/risks")
    assert resp.status_code == 200
    risks = resp.json()
    assert isinstance(risks, list)
    assert len(risks) >= 1


def test_list_risks_for_contract_not_found():
    resp = client.get("/contracts/99999999/risks")
    assert resp.status_code == 404


def test_list_risks_empty_for_new_contract(db_session):
    """A brand-new contract with no clauses should return empty risks list."""
    c = create_contract(db_session, filename="empty_risks.pdf")
    resp = client.get(f"/contracts/{c.id}/risks")
    assert resp.status_code == 200
    assert resp.json() == []
    delete_contract(db_session, c.id)


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /risks/{risk_id}
# ──────────────────────────────────────────────────────────────────────────────

def test_delete_risk(contract_with_clause):
    clause_id = contract_with_clause["clause"]["id"]
    risk = client.post(
        f"/clauses/{clause_id}/risks",
        json={"risk_type": "To delete", "risk_level": "LOW"},
    ).json()
    risk_id = risk["id"]

    resp = client.delete(f"/risks/{risk_id}")
    assert resp.status_code == 204

    # Verify risk is gone from clause list
    remaining = client.get(f"/clauses/{clause_id}/risks").json()
    assert all(r["id"] != risk_id for r in remaining)


def test_delete_risk_not_found():
    resp = client.delete("/risks/99999999")
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# Cascade: deleting a contract removes clauses and risks
# ──────────────────────────────────────────────────────────────────────────────

def test_delete_contract_cascades_clauses_and_risks(db_session):
    """Deleting a contract must cascade down to clauses and then to risks."""
    # Build: contract → clause → risk
    c = create_contract(db_session, filename="cascade_test.pdf")
    clause_resp = client.post(
        f"/contracts/{c.id}/clauses",
        json={"text": "Cascade clause.", "clause_number": "1.1"},
    )
    clause_id = clause_resp.json()["id"]
    risk_resp = client.post(
        f"/clauses/{clause_id}/risks",
        json={"risk_type": "Cascade risk", "risk_level": "HIGH"},
    )
    risk_id = risk_resp.json()["id"]

    # Delete the contract
    del_resp = client.delete(f"/contracts/{c.id}")
    assert del_resp.status_code == 204

    # Clause should be gone
    assert client.get(f"/clauses/{clause_id}").status_code == 404
    # Contract should be gone
    assert client.get(f"/contracts/{c.id}").status_code == 404
