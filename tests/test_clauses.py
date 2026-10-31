"""
tests/test_clauses.py

Tests for the Clauses API:
- POST   /contracts/{contract_id}/clauses
- GET    /contracts/{contract_id}/clauses
- GET    /clauses/{clause_id}
- DELETE /clauses/{clause_id}  (including cascade to risks)
"""
import pytest

from tests.conftest import make_pdf_upload


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _create_contract(client):
    resp = client.post("/contracts/upload", files=make_pdf_upload("clause_test.pdf"))
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_clause(client, contract_id, text="Default clause text.", **kwargs):
    payload = {"text": text, **kwargs}
    resp = client.post(f"/contracts/{contract_id}/clauses", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# POST /contracts/{contract_id}/clauses
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateClause:
    def test_create_under_valid_contract(self, client):
        cid = _create_contract(client)
        resp = client.post(
            f"/contracts/{cid}/clauses",
            json={
                "text": "All information shared shall remain confidential.",
                "clause_number": "1.1",
                "clause_type": "Confidentiality",
                "page_number": 2,
                "confidence": 0.97,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["contract_id"] == cid
        assert data["clause_number"] == "1.1"
        assert data["clause_type"] == "Confidentiality"
        assert data["page_number"] == 2
        assert data["confidence"] == 0.97
        assert isinstance(data["id"], int)

    def test_create_under_nonexistent_contract_returns_404(self, client):
        resp = client.post(
            "/contracts/99999999/clauses",
            json={"text": "Some clause."},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_create_missing_required_text_returns_422(self, client):
        cid = _create_contract(client)
        resp = client.post(
            f"/contracts/{cid}/clauses",
            json={"clause_type": "Indemnity"},  # text is required
        )
        assert resp.status_code == 422

    def test_create_clause_optional_fields_default_null(self, client):
        """Only text is required; all other fields should default to null."""
        cid = _create_contract(client)
        resp = client.post(f"/contracts/{cid}/clauses", json={"text": "Minimal clause."})
        assert resp.status_code == 201
        data = resp.json()
        assert data["clause_number"] is None
        assert data["clause_type"] is None
        assert data["page_number"] is None
        assert data["confidence"] is None


# ─────────────────────────────────────────────────────────────────────────────
# GET /contracts/{contract_id}/clauses
# ─────────────────────────────────────────────────────────────────────────────

class TestListClauses:
    def test_list_empty_for_new_contract(self, client):
        cid = _create_contract(client)
        resp = client.get(f"/contracts/{cid}/clauses")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_correct_set(self, client):
        cid = _create_contract(client)
        _create_clause(client, cid, text="Clause one.", clause_number="1.1")
        _create_clause(client, cid, text="Clause two.", clause_number="1.2")
        _create_clause(client, cid, text="Clause three.", clause_number="1.3")

        resp = client.get(f"/contracts/{cid}/clauses")
        assert resp.status_code == 200
        clauses = resp.json()
        assert len(clauses) == 3
        assert all(c["contract_id"] == cid for c in clauses)
        numbers = {c["clause_number"] for c in clauses}
        assert numbers == {"1.1", "1.2", "1.3"}

    def test_list_isolates_between_contracts(self, client):
        """Clauses from one contract must not appear in another's list."""
        cid1 = _create_contract(client)
        cid2 = _create_contract(client)
        _create_clause(client, cid1, text="Only for contract 1.")

        resp = client.get(f"/contracts/{cid2}/clauses")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_nonexistent_contract_returns_404(self, client):
        resp = client.get("/contracts/99999999/clauses")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# GET /clauses/{clause_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestGetClause:
    def test_get_existing_clause(self, client):
        cid = _create_contract(client)
        created = _create_clause(client, cid, text="Specific clause.", clause_number="2.1")
        resp = client.get(f"/clauses/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]
        assert resp.json()["clause_number"] == "2.1"

    def test_get_nonexistent_clause_returns_404(self, client):
        resp = client.get("/clauses/99999999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /clauses/{clause_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteClause:
    def test_delete_returns_204(self, client):
        cid = _create_contract(client)
        clause = _create_clause(client, cid, text="To delete.")
        resp = client.delete(f"/clauses/{clause['id']}")
        assert resp.status_code == 204

    def test_deleted_clause_is_unfetchable(self, client):
        cid = _create_contract(client)
        clause = _create_clause(client, cid, text="Gone soon.")
        client.delete(f"/clauses/{clause['id']}")
        assert client.get(f"/clauses/{clause['id']}").status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/clauses/99999999")
        assert resp.status_code == 404

    def test_delete_clause_cascades_to_risks(self, client):
        """Deleting a clause must remove all its child risks."""
        cid = _create_contract(client)
        clause = _create_clause(client, cid, text="Cascade clause.")
        clid = clause["id"]

        # Add two risks
        r1 = client.post(f"/clauses/{clid}/risks",
                         json={"risk_type": "Risk Alpha", "risk_level": "HIGH"})
        r2 = client.post(f"/clauses/{clid}/risks",
                         json={"risk_type": "Risk Beta", "risk_level": "LOW"})
        assert r1.status_code == 201
        assert r2.status_code == 201

        # Confirm risks exist
        risks_before = client.get(f"/clauses/{clid}/risks").json()
        assert len(risks_before) == 2

        # Delete clause
        assert client.delete(f"/clauses/{clid}").status_code == 204

        # Clause is gone — any attempt to fetch its risks returns 404 (clause not found)
        assert client.get(f"/clauses/{clid}/risks").status_code == 404

    def test_delete_clause_does_not_remove_other_clauses(self, client):
        """Only the targeted clause is removed; siblings must remain."""
        cid = _create_contract(client)
        cl1 = _create_clause(client, cid, text="Keep me.")
        cl2 = _create_clause(client, cid, text="Delete me.")

        client.delete(f"/clauses/{cl2['id']}")
        assert client.get(f"/clauses/{cl1['id']}").status_code == 200
