"""
tests/test_contracts.py

Tests for the Contracts API:
- POST   /contracts/upload
- GET    /contracts
- GET    /contracts/{id}
- PATCH  /contracts/{id}
- DELETE /contracts/{id}
- DELETE cascade to clauses and risks
"""
import io
import pytest

from tests.conftest import make_pdf_upload


# ─────────────────────────────────────────────────────────────────────────────
# POST /contracts/upload
# ─────────────────────────────────────────────────────────────────────────────

class TestUploadContract:
    def test_upload_valid_pdf_returns_201(self, client):
        resp = client.post("/contracts/upload", files=make_pdf_upload("agreement.pdf"))
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "agreement.pdf"
        assert data["status"] == "uploaded"
        assert isinstance(data["id"], int)
        assert "upload_date" in data

    def test_upload_non_pdf_content_type_returns_400(self, client):
        files = {"file": ("report.docx", io.BytesIO(b"word content"), "application/msword")}
        resp = client.post("/contracts/upload", files=files)
        assert resp.status_code == 400
        assert "Invalid file type" in resp.json()["detail"]

    def test_upload_pdf_wrong_extension_returns_400(self, client):
        files = {"file": ("contract.txt", io.BytesIO(b"text content"), "application/pdf")}
        resp = client.post("/contracts/upload", files=files)
        assert resp.status_code == 400
        assert "extension" in resp.json()["detail"].lower()

    def test_upload_empty_pdf_returns_400(self, client):
        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        resp = client.post("/contracts/upload", files=files)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# GET /contracts
# ─────────────────────────────────────────────────────────────────────────────

class TestListContracts:
    def test_list_empty(self, client):
        resp = client.get("/contracts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_uploaded_contracts(self, client):
        client.post("/contracts/upload", files=make_pdf_upload("a.pdf"))
        client.post("/contracts/upload", files=make_pdf_upload("b.pdf"))
        resp = client.get("/contracts")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_pagination(self, client):
        for i in range(5):
            client.post("/contracts/upload", files=make_pdf_upload(f"file{i}.pdf"))
        resp = client.get("/contracts?skip=2&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ─────────────────────────────────────────────────────────────────────────────
# GET /contracts/{id}
# ─────────────────────────────────────────────────────────────────────────────

class TestGetContract:
    def test_get_existing_contract(self, client):
        created = client.post("/contracts/upload", files=make_pdf_upload("fetch.pdf")).json()
        resp = client.get(f"/contracts/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]
        assert resp.json()["filename"] == "fetch.pdf"

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/contracts/99999999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /contracts/{id}
# ─────────────────────────────────────────────────────────────────────────────

class TestPatchContract:
    def test_patch_status_and_score(self, client):
        created = client.post("/contracts/upload", files=make_pdf_upload("patch.pdf")).json()
        resp = client.patch(
            f"/contracts/{created['id']}",
            json={"status": "analyzed", "overall_score": 78.5, "contract_type": "NDA"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "analyzed"
        assert data["overall_score"] == 78.5
        assert data["contract_type"] == "NDA"

    def test_patch_partial_leaves_other_fields(self, client):
        created = client.post("/contracts/upload", files=make_pdf_upload("partial.pdf")).json()
        # Set score first
        client.patch(f"/contracts/{created['id']}", json={"overall_score": 90.0})
        # Patch only status — score must stay
        resp = client.patch(f"/contracts/{created['id']}", json={"status": "reviewed"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reviewed"
        assert data["overall_score"] == 90.0

    def test_patch_nonexistent_returns_404(self, client):
        resp = client.patch("/contracts/99999999", json={"status": "analyzed"})
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /contracts/{id}
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteContract:
    def test_delete_returns_204(self, client):
        created = client.post("/contracts/upload", files=make_pdf_upload("delete.pdf")).json()
        resp = client.delete(f"/contracts/{created['id']}")
        assert resp.status_code == 204

    def test_delete_makes_contract_unfetchable(self, client):
        created = client.post("/contracts/upload", files=make_pdf_upload("gone.pdf")).json()
        client.delete(f"/contracts/{created['id']}")
        assert client.get(f"/contracts/{created['id']}").status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/contracts/99999999")
        assert resp.status_code == 404

    def test_delete_cascades_to_clauses_and_risks(self, client):
        """Deleting a contract must remove its clauses and risks (ON DELETE CASCADE)."""
        # Build: contract → clause → 2 risks
        contract = client.post("/contracts/upload", files=make_pdf_upload("cascade.pdf")).json()
        cid = contract["id"]

        clause = client.post(
            f"/contracts/{cid}/clauses",
            json={"text": "Cascade test clause.", "clause_number": "1.1"},
        ).json()
        clid = clause["id"]

        client.post(f"/clauses/{clid}/risks", json={"risk_type": "Risk A", "risk_level": "HIGH"})
        client.post(f"/clauses/{clid}/risks", json={"risk_type": "Risk B", "risk_level": "LOW"})

        # Confirm they exist
        assert client.get(f"/clauses/{clid}").status_code == 200
        assert len(client.get(f"/clauses/{clid}/risks").json()) == 2

        # Delete contract
        assert client.delete(f"/contracts/{cid}").status_code == 204

        # Clause and contract must be gone
        assert client.get(f"/contracts/{cid}").status_code == 404
        assert client.get(f"/clauses/{clid}").status_code == 404
