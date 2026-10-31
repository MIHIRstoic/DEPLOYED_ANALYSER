"""
tests/test_risks.py

Tests for the Risks API:
- POST   /clauses/{clause_id}/risks
- GET    /clauses/{clause_id}/risks
- GET    /contracts/{contract_id}/risks
- DELETE /risks/{risk_id}
- GET    /contracts/{contract_id}/report  (nested structure)
"""
import pytest

from tests.conftest import make_pdf_upload


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _setup_contract_clause(client, pdf_name="risk_test.pdf", clause_text="Clause for risk tests."):
    contract = client.post("/contracts/upload", files=make_pdf_upload(pdf_name)).json()
    clause = client.post(
        f"/contracts/{contract['id']}/clauses",
        json={"text": clause_text, "clause_number": "1.1", "clause_type": "Indemnity"},
    ).json()
    return contract["id"], clause["id"]


def _create_risk(client, clause_id, risk_type="Default Risk", risk_level="MEDIUM", **kwargs):
    payload = {"risk_type": risk_type, "risk_level": risk_level, **kwargs}
    resp = client.post(f"/clauses/{clause_id}/risks", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# POST /clauses/{clause_id}/risks
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateRisk:
    def test_create_under_valid_clause(self, client):
        _, clid = _setup_contract_clause(client)
        resp = client.post(
            f"/clauses/{clid}/risks",
            json={
                "risk_type": "Unlimited Liability",
                "risk_level": "HIGH",
                "reason": "No indemnity cap.",
                "evidence": "without limitation",
                "recommendation": "Add a cap clause.",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["clause_id"] == clid
        assert data["risk_type"] == "Unlimited Liability"
        assert data["risk_level"] == "HIGH"
        assert data["reason"] == "No indemnity cap."
        assert data["evidence"] == "without limitation"
        assert isinstance(data["id"], int)

    def test_create_under_nonexistent_clause_returns_404(self, client):
        resp = client.post(
            "/clauses/99999999/risks",
            json={"risk_type": "Some Risk", "risk_level": "LOW"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_create_risk_all_fields_optional_except_none(self, client):
        """All fields are optional — empty body should still succeed."""
        _, clid = _setup_contract_clause(client)
        resp = client.post(f"/clauses/{clid}/risks", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert data["clause_id"] == clid
        assert data["risk_type"] is None
        assert data["risk_level"] is None


# ─────────────────────────────────────────────────────────────────────────────
# GET /clauses/{clause_id}/risks
# ─────────────────────────────────────────────────────────────────────────────

class TestListRisksForClause:
    def test_list_empty_for_new_clause(self, client):
        _, clid = _setup_contract_clause(client)
        resp = client.get(f"/clauses/{clid}/risks")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_correct_set(self, client):
        _, clid = _setup_contract_clause(client)
        _create_risk(client, clid, "Risk 1", "HIGH")
        _create_risk(client, clid, "Risk 2", "MEDIUM")
        _create_risk(client, clid, "Risk 3", "LOW")

        resp = client.get(f"/clauses/{clid}/risks")
        assert resp.status_code == 200
        risks = resp.json()
        assert len(risks) == 3
        assert all(r["clause_id"] == clid for r in risks)
        types = {r["risk_type"] for r in risks}
        assert types == {"Risk 1", "Risk 2", "Risk 3"}

    def test_list_nonexistent_clause_returns_404(self, client):
        resp = client.get("/clauses/99999999/risks")
        assert resp.status_code == 404

    def test_risks_isolated_between_clauses(self, client):
        cid, cl1 = _setup_contract_clause(client, "iso.pdf", "Clause one.")
        cl2 = client.post(
            f"/contracts/{cid}/clauses",
            json={"text": "Clause two."},
        ).json()["id"]

        _create_risk(client, cl1, "Only for clause 1", "HIGH")

        resp = client.get(f"/clauses/{cl2}/risks")
        assert resp.status_code == 200
        assert resp.json() == []


# ─────────────────────────────────────────────────────────────────────────────
# GET /contracts/{contract_id}/risks
# ─────────────────────────────────────────────────────────────────────────────

class TestListRisksForContract:
    def test_list_empty_for_new_contract(self, client):
        cid, _ = _setup_contract_clause(client)
        # Contract has a clause but no risks yet
        resp = client.get(f"/contracts/{cid}/risks")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_aggregates_risks_across_multiple_clauses(self, client):
        """Risks from all clauses under the contract must be returned together."""
        cid, cl1 = _setup_contract_clause(client, "multi.pdf", "Clause A.")
        cl2 = client.post(
            f"/contracts/{cid}/clauses",
            json={"text": "Clause B."},
        ).json()["id"]

        r1 = _create_risk(client, cl1, "Risk from Clause A", "HIGH")
        r2 = _create_risk(client, cl2, "Risk from Clause B", "LOW")
        r3 = _create_risk(client, cl2, "Another risk from Clause B", "MEDIUM")

        resp = client.get(f"/contracts/{cid}/risks")
        assert resp.status_code == 200
        risks = resp.json()
        assert len(risks) == 3
        ids = {r["id"] for r in risks}
        assert {r1["id"], r2["id"], r3["id"]} == ids

    def test_risks_isolated_between_contracts(self, client):
        """Risks from contract 1 must not appear in contract 2's list."""
        cid1, cl1 = _setup_contract_clause(client, "c1.pdf", "C1 clause.")
        cid2, _ = _setup_contract_clause(client, "c2.pdf", "C2 clause.")

        _create_risk(client, cl1, "Contract 1 risk", "HIGH")

        resp = client.get(f"/contracts/{cid2}/risks")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_nonexistent_contract_returns_404(self, client):
        resp = client.get("/contracts/99999999/risks")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /risks/{risk_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteRisk:
    def test_delete_returns_204(self, client):
        _, clid = _setup_contract_clause(client)
        risk = _create_risk(client, clid)
        resp = client.delete(f"/risks/{risk['id']}")
        assert resp.status_code == 204

    def test_deleted_risk_absent_from_clause_list(self, client):
        _, clid = _setup_contract_clause(client)
        r1 = _create_risk(client, clid, "Keep", "LOW")
        r2 = _create_risk(client, clid, "Delete", "HIGH")

        client.delete(f"/risks/{r2['id']}")
        remaining = client.get(f"/clauses/{clid}/risks").json()
        assert len(remaining) == 1
        assert remaining[0]["id"] == r1["id"]

    def test_delete_nonexistent_risk_returns_404(self, client):
        resp = client.delete("/risks/99999999")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# GET /contracts/{contract_id}/report  (nested structure)
# ─────────────────────────────────────────────────────────────────────────────

class TestContractReport:
    def test_report_404_for_missing_contract(self, client):
        resp = client.get("/contracts/99999999/report")
        assert resp.status_code == 404

    def test_report_empty_clauses_and_risks(self, client):
        """A new contract with no clauses returns an empty clauses list."""
        contract = client.post("/contracts/upload", files=make_pdf_upload("empty_report.pdf")).json()
        resp = client.get(f"/contracts/{contract['id']}/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == contract["id"]
        assert data["clauses"] == []

    def test_report_nested_structure(self, client):
        """Full contract → clauses[] → risks[] nesting is correct."""
        # 1 contract, 2 clauses, 2 risks each
        contract = client.post("/contracts/upload", files=make_pdf_upload("report.pdf")).json()
        cid = contract["id"]

        cl1 = client.post(
            f"/contracts/{cid}/clauses",
            json={"text": "Party A indemnifies Party B.", "clause_number": "1.1",
                  "clause_type": "Indemnity", "page_number": 1, "confidence": 0.95},
        ).json()
        cl2 = client.post(
            f"/contracts/{cid}/clauses",
            json={"text": "Governed by laws of Delaware.", "clause_number": "2.1",
                  "clause_type": "Governing Law", "page_number": 3, "confidence": 0.88},
        ).json()

        client.post(f"/clauses/{cl1['id']}/risks",
                    json={"risk_type": "Unlimited Liability", "risk_level": "HIGH",
                          "reason": "No cap", "recommendation": "Add a cap."})
        client.post(f"/clauses/{cl1['id']}/risks",
                    json={"risk_type": "One-sided Obligation", "risk_level": "MEDIUM"})
        client.post(f"/clauses/{cl2['id']}/risks",
                    json={"risk_type": "Jurisdiction Risk", "risk_level": "LOW"})
        client.post(f"/clauses/{cl2['id']}/risks",
                    json={"risk_type": "Vague Scope", "risk_level": "MEDIUM"})

        resp = client.get(f"/contracts/{cid}/report")
        assert resp.status_code == 200
        report = resp.json()

        # Top-level contract fields
        assert report["id"] == cid
        assert report["filename"] == "report.pdf"
        assert "upload_date" in report

        # Clauses
        assert len(report["clauses"]) == 2

        # Each clause must carry its risks
        for clause in report["clauses"]:
            assert "risks" in clause
            assert len(clause["risks"]) == 2
            assert all("risk_level" in r for r in clause["risks"])
            assert all(r["clause_id"] == clause["id"] for r in clause["risks"])

    def test_report_clause_with_no_risks(self, client):
        """A clause with zero risks should appear with an empty risks list."""
        contract = client.post("/contracts/upload", files=make_pdf_upload("norisk.pdf")).json()
        cid = contract["id"]

        client.post(f"/contracts/{cid}/clauses",
                    json={"text": "Clean clause, no risks."})

        resp = client.get(f"/contracts/{cid}/report")
        assert resp.status_code == 200
        report = resp.json()
        assert len(report["clauses"]) == 1
        assert report["clauses"][0]["risks"] == []
