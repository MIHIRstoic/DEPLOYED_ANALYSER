# AI-Based Legal Contract Analysis and Risk Detection System — Backend

Backend service built with **FastAPI**, **SQLAlchemy 2**, **Alembic**, and **Python 3.11+**.  
Provides a REST API for uploading legal contracts, managing extracted clauses and detected risks, and serving a nested aggregated report.

> **Scope note**: This project has no authentication, Docker configuration, or deployment files. Those are out of scope for the current stage.

---

## Project Structure

```text
backend/
├── alembic/                    # Alembic migration environment
│   ├── versions/               # Auto-generated migration scripts
│   └── env.py                  # Reads DATABASE_URL from app.core.config.Settings
├── alembic.ini                 # Alembic project configuration
├── app/
│   ├── main.py                 # FastAPI app instance; all routers registered here
│   ├── core/
│   │   ├── config.py           # Settings class (loads .env via pydantic-settings)
│   │   └── database.py         # Engine, SessionLocal, Base, get_db() dependency
│   ├── models/
│   │   ├── contract.py         # Contract ORM model
│   │   ├── clause.py           # Clause ORM model (FK → contracts)
│   │   └── risk.py             # Risk ORM model   (FK → clauses)
│   ├── schemas/
│   │   ├── contract.py         # ContractBase/Create/Update/Response + ContractReport
│   │   ├── clause.py           # ClauseBase/Create/Update/Response
│   │   └── risk.py             # RiskBase/Create/Update/Response
│   ├── crud/
│   │   ├── contract.py         # CRUD helpers + get_contract_with_report (eager load)
│   │   ├── clause.py           # Clause CRUD (+ future risk-engine hook)
│   │   └── risk.py             # Risk CRUD   (+ future LLM-explanation hook)
│   ├── api/
│   │   ├── contracts.py        # /contracts router  (upload, list, get, patch, delete, report)
│   │   ├── clauses.py          # /clauses router    (create, list, get, delete)
│   │   └── risks.py            # /risks router      (create, list by clause/contract, delete)
│   └── services/
│       └── file_handler.py     # validate_pdf() + save_temp_file()
├── tests/
│   ├── conftest.py             # SQLite in-memory test DB, dependency override, fixtures
│   ├── test_contracts.py       # Contract API integration tests
│   ├── test_clauses.py         # Clause API integration tests
│   ├── test_risks.py           # Risk API + /report integration tests
│   ├── test_crud.py            # CRUD layer unit tests (real PostgreSQL)
│   ├── test_database.py        # Engine / session tests
│   ├── test_health.py          # Health check test
│   └── test_models.py          # ORM model metadata tests
├── uploads/                    # Uploaded PDF files (git-ignored)
├── .env.example                # Environment variable template — copy to .env
├── .env                        # Your local settings (never commit this)
├── requirements.txt            # Pinned dependencies
└── README.md                   # This file
```

---

## API Endpoints

| Method   | Path                              | Description                                      |
|----------|-----------------------------------|--------------------------------------------------|
| `GET`    | `/health`                         | Liveness check                                   |
| `POST`   | `/contracts/upload`               | Upload a PDF; creates a Contract record          |
| `GET`    | `/contracts`                      | List all contracts (supports `skip` / `limit`)   |
| `GET`    | `/contracts/{id}`                 | Get a contract by ID                             |
| `PATCH`  | `/contracts/{id}`                 | Update contract metadata                         |
| `DELETE` | `/contracts/{id}`                 | Delete contract + cascade clauses + risks        |
| `GET`    | `/contracts/{id}/report`          | Full nested report: contract → clauses → risks   |
| `POST`   | `/contracts/{id}/clauses`         | Create a clause under a contract                 |
| `GET`    | `/contracts/{id}/clauses`         | List all clauses for a contract                  |
| `GET`    | `/clauses/{id}`                   | Get a clause by ID                               |
| `DELETE` | `/clauses/{id}`                   | Delete clause + cascade risks                    |
| `POST`   | `/clauses/{id}/risks`             | Create a risk under a clause                     |
| `GET`    | `/clauses/{id}/risks`             | List risks for a clause                          |
| `GET`    | `/contracts/{id}/risks`           | List all risks across all clauses of a contract  |
| `DELETE` | `/risks/{id}`                     | Delete a single risk                             |

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+** running locally (or a remote instance)
- `pip` package manager

---

### Step 1 — Clone and enter the backend directory

```powershell
# Windows (PowerShell)
cd backend
```

```bash
# Linux / macOS
cd backend
```

---

### Step 2 — Create and activate a virtual environment

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Configure environment variables

Copy the template and fill in your PostgreSQL credentials:

```powershell
# Windows (PowerShell)
Copy-Item .env.example .env
```

```bash
# Linux / macOS
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/<database_name>
PROJECT_NAME=AI Legal Contract Analyzer
```

> **Tip**: create the database first if it doesn't exist:  
> `createdb contract_analyzer` (or via pgAdmin / psql).

---

### Step 5 — Run database migrations

```bash
alembic upgrade head
```

This creates the `contracts`, `clauses`, and `risks` tables with all foreign keys and `ON DELETE CASCADE` constraints.

---

### Step 6 — Start the development server

```bash
uvicorn app.main:app --reload
```

The server starts at:

| URL | Purpose |
|-----|---------|
| <http://127.0.0.1:8000/health> | Liveness check |
| <http://127.0.0.1:8000/docs>   | Interactive Swagger UI |
| <http://127.0.0.1:8000/redoc>  | ReDoc documentation |

---

### Step 7 — Run the test suite

Tests use an **SQLite in-memory database** — no PostgreSQL connection required.

```bash
pytest -v
```

Expected output: **93 passed** (or more as the suite grows).

---

## Database Migrations Reference

```bash
# Generate a new migration after changing ORM models
alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
alembic upgrade head

# Roll back the most recent migration
alembic downgrade -1

# Show migration history
alembic history
```

---

## AI Pipeline — Future Integration Points

The codebase has clearly marked `# ── FUTURE HOOK` comments at the exact points where AI components will plug in:

| File | Hook | Component |
|------|------|-----------|
| `app/api/contracts.py` — `upload_contract()` | After file save | **PDF Text Extraction / OCR** (`pdfplumber`, PyMuPDF, pytesseract) |
| `app/api/contracts.py` — `upload_contract()` | After extraction | **Clause Segmentation & Classification** (NLP model populates `clause_type`, `confidence`) |
| `app/crud/clause.py` — `create_clause()` | After clause is persisted | **Risk Detection Engine** (rule-based or ML; populates `risk_type`, `risk_level`, `evidence`) |
| `app/crud/risk.py` — `create_risk()` | After risk is persisted | **LLM Explanations** (GPT-4o / Claude; populates `reason`, `recommendation`) |

Search for `FUTURE HOOK` in the codebase to locate each comment.
