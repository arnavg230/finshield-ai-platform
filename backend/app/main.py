"""
FinShield AI - Backend API (Member 1).

Run with:
    uvicorn app.main:app --reload

Swagger UI:  http://127.0.0.1:8000/docs
ReDoc:       http://127.0.0.1:8000/redoc
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import AML_WEIGHT, ML_MODEL_NAME, ML_WEIGHT
from app.database import Base, engine
from app.routers import (
    admin, alerts, analytics, auth, cases, transactions, aml_testing
)
from app.services import aml_service
from app.services.ml_service import ml_service

DESCRIPTION = """
Backend for the FinShield AI financial crime detection and investigation platform.

**What this API does**

* Registration, login with JWT and role based access control
* Transaction submission and storage
* Fraud prediction using the PaySim models trained by Member 2
* SHAP explanations for those predictions
* AML rule, behaviour and network analysis from Member 4's module
* A hybrid risk score that combines the ML and AML results
* Alerts, investigation cases and an audit trail

**Roles**

| Role | What it can do |
| --- | --- |
| `CUSTOMER` | Submit transactions and view its own transactions |
| `ANALYST` | View all transactions and alerts, open and work on cases |
| `COMPLIANCE` | View analytics, alerts and the audit trail |
| `ADMIN` | Everything, plus user management and system settings |

Use the **Authorize** button with a username and password to try the endpoints.
"""

# Create the tables on startup. The project is a prototype, so a migration
# tool like Alembic is not used.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FinShield AI - Backend API",
    description=DESCRIPTION,
    version="0.6.0",
    contact={"name": "Member 1 - Backend and Security"},
)

# The React frontend (Member 3) will run on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(alerts.router)
app.include_router(cases.router)
app.include_router(analytics.router)
app.include_router(admin.router)
app.include_router(aml_testing.router)


@app.get("/", tags=["System"])
def root():
    return {
        "name": "FinShield AI Backend",
        "version": app.version,
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health():
    """Quick check that the database, the ML models and the AML module loaded."""
    return {
        "status": "ok",
        "ml_models_loaded": ml_service.available_models(),
        "ml_active_model": ML_MODEL_NAME,
        "ml_load_error": ml_service.load_error,
        "aml_module_available": aml_service.AML_AVAILABLE,
        "aml_import_error": aml_service.AML_IMPORT_ERROR,
        "hybrid_weights": {"ml": ML_WEIGHT, "aml": AML_WEIGHT},
    }
