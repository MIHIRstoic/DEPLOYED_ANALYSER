import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, SessionLocal
from app.crud.contract import delete_contract, get_contract


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def make_pdf_file(name: str = "test_contract.pdf", content: bytes = b"%PDF-1.4 test") -> tuple:
    """Return (filename, file-like, content-type) for multipart upload."""
    return (name, io.BytesIO(content), "application/pdf")


# ---------------------------------------------------------------------------
# POST /contracts/upload
# ---------------------------------------------------------------------------

def test_upload_valid_pdf(client: TestClient, db_session: Session):
    files = {"file": make_pdf_file()}
    response = client.post("/contracts/upload", files=files)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["filename"] == "test_contract.pdf"
    assert data["status"] == "uploaded"
    assert "id" in data
    assert "upload_date" in data
    # Cleanup
    delete_contract(db_session, data["id"])


def test_upload_non_pdf_content_type(client: TestClient):
    files = {"file": ("report.docx", io.BytesIO(b"some word content"), "application/msword")}
    response = client.post("/contracts/upload", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_pdf_wrong_extension(client: TestClient):
    files = {"file": ("contract.txt", io.BytesIO(b"some text"), "application/pdf")}
    response = client.post("/contracts/upload", files=files)
    assert response.status_code == 400
    assert "extension" in response.json()["detail"].lower()


def test_upload_empty_pdf(client: TestClient):
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/contracts/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /contracts
# ---------------------------------------------------------------------------

def test_list_contracts(client: TestClient, db_session: Session):
    # Upload one first
    files = {"file": make_pdf_file("list_test.pdf")}
    upload_resp = client.post("/contracts/upload", files=files)
    assert upload_resp.status_code == 201
    created_id = upload_resp.json()["id"]

    response = client.get("/contracts")
    assert response.status_code == 200
    contracts = response.json()
    assert isinstance(contracts, list)
    ids = [c["id"] for c in contracts]
    assert created_id in ids

    delete_contract(db_session, created_id)


def test_list_contracts_pagination(client: TestClient):
    response = client.get("/contracts?skip=0&limit=5")
    assert response.status_code == 200
    assert len(response.json()) <= 5


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}
# ---------------------------------------------------------------------------

def test_get_contract_found(client: TestClient, db_session: Session):
    files = {"file": make_pdf_file("get_test.pdf")}
    created = client.post("/contracts/upload", files=files).json()

    response = client.get(f"/contracts/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["filename"] == "get_test.pdf"

    delete_contract(db_session, created["id"])


def test_get_contract_not_found(client: TestClient):
    response = client.get("/contracts/99999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PATCH /contracts/{contract_id}
# ---------------------------------------------------------------------------

def test_patch_contract(client: TestClient, db_session: Session):
    files = {"file": make_pdf_file("patch_test.pdf")}
    created = client.post("/contracts/upload", files=files).json()

    patch_data = {"status": "analyzed", "overall_score": 78.5, "contract_type": "NDA"}
    response = client.patch(f"/contracts/{created['id']}", json=patch_data)
    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "analyzed"
    assert updated["overall_score"] == 78.5
    assert updated["contract_type"] == "NDA"

    delete_contract(db_session, created["id"])


def test_patch_contract_not_found(client: TestClient):
    response = client.patch("/contracts/99999999", json={"status": "analyzed"})
    assert response.status_code == 404


def test_patch_contract_partial(client: TestClient, db_session: Session):
    """PATCH only updates provided fields, others remain unchanged."""
    files = {"file": make_pdf_file("partial_patch.pdf")}
    created = client.post("/contracts/upload", files=files).json()

    # First set overall_score
    client.patch(f"/contracts/{created['id']}", json={"overall_score": 90.0})
    # Then patch only status — score should remain
    response = client.patch(f"/contracts/{created['id']}", json={"status": "reviewed"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reviewed"
    assert data["overall_score"] == 90.0

    delete_contract(db_session, created["id"])


# ---------------------------------------------------------------------------
# DELETE /contracts/{contract_id}
# ---------------------------------------------------------------------------

def test_delete_contract(client: TestClient):
    files = {"file": make_pdf_file("delete_test.pdf")}
    created = client.post("/contracts/upload", files=files).json()

    response = client.delete(f"/contracts/{created['id']}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/contracts/{created['id']}")
    assert get_response.status_code == 404


def test_delete_contract_not_found(client: TestClient):
    response = client.delete("/contracts/99999999")
    assert response.status_code == 404
