"""
tests/conftest.py

Central test configuration:
- Creates a SQLite in-memory engine with a single shared connection so that
  the test fixtures and API routes all see the same in-memory state.
- Overrides the FastAPI get_db dependency to use the test session.
- Provides `client` (TestClient) and `db` (Session) fixtures.
- Isolates every test function via a transaction rollback strategy.

Why a single connection?
  sqlite:// (pure in-memory) creates tables on one connection; when a second
  connection is opened the database appears empty.  Binding the sessionmaker
  to a single, reused connection avoids this problem entirely.
"""

import io
import pytest

from sqlalchemy import create_engine, event, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db

# ---------------------------------------------------------------------------
# One engine, one connection, one in-memory database for the entire test run.
# StaticPool reuses the exact same underlying connection for every checkout,
# which means all sessions see the tables created by Base.metadata.create_all.
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,       # ← key: single shared connection
)

# Enforce FK constraints on SQLite (off by default)
@event.listens_for(engine, "connect")
def _set_sqlite_fk(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Session-scoped: create all tables once before ANY test runs.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Function-scoped: wrap every test in a transaction that is rolled back,
# giving each test a clean slate without recreating tables.
# ---------------------------------------------------------------------------
@pytest.fixture
def db() -> Session:
    """
    Raw SQLAlchemy session for a single test.
    Everything is rolled back after the test so the next test starts fresh.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# TestClient with dependency override pointing at the test session.
# ---------------------------------------------------------------------------
@pytest.fixture
def client(db: Session) -> TestClient:
    """
    FastAPI TestClient whose get_db is overridden to use the test session.
    The same session is shared, so data written inside the test is immediately
    visible to the API routes within the same test.
    """
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helper: minimal fake PDF bytes and upload dict
# ---------------------------------------------------------------------------
FAKE_PDF_BYTES = b"%PDF-1.4 1 0 obj<</Type /Catalog>>endobj\n%%EOF"


def make_pdf_upload(filename: str = "contract.pdf") -> dict:
    """Return a files dict suitable for client.post(..., files=...)."""
    return {"file": (filename, io.BytesIO(FAKE_PDF_BYTES), "application/pdf")}
