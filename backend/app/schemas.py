"""Pydantic request and response models (these also produce the Swagger docs)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ROLE_CUSTOMER

ORM = ConfigDict(from_attributes=True)


# --- Users and authentication ----------------------------------------------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["analyst1"])
    email: EmailStr = Field(examples=["analyst1@thapar.edu"])
    password: str = Field(min_length=6, examples=["Password@123"])
    full_name: str | None = Field(default=None, examples=["Test Analyst"])
    role: str = Field(default=ROLE_CUSTOMER, examples=["ANALYST"])


class UserOut(BaseModel):
    model_config = ORM
    id: int
    username: str
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime


class RoleUpdate(BaseModel):
    role: str = Field(examples=["COMPLIANCE"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


# --- Transactions -----------------------------------------------------------
class TransactionCreate(BaseModel):
    step: int = Field(default=1, ge=1, description="PaySim hour step")
    type: str = Field(
        examples=["TRANSFER"],
        description="One of CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER",
    )
    amount: float = Field(gt=0, examples=[181000.0])
    nameOrig: str = Field(examples=["C1231006815"], description="Sender account")
    oldbalanceOrg: float = Field(default=0.0, ge=0, examples=[181000.0])
    newbalanceOrig: float = Field(default=0.0, ge=0, examples=[0.0])
    nameDest: str = Field(examples=["C1666544295"], description="Receiver account")
    oldbalanceDest: float = Field(default=0.0, ge=0, examples=[0.0])
    newbalanceDest: float = Field(default=0.0, ge=0, examples=[0.0])
    isFlaggedFraud: int = Field(default=0, ge=0, le=1)
    currency: str = Field(default="US Dollar")
    timestamp: datetime | None = Field(
        default=None, description="Defaults to the current server time."
    )


class TransactionOut(BaseModel):
    model_config = ORM
    id: int
    txn_ref: str
    step: int
    txn_type: str
    amount: float
    name_orig: str
    oldbalance_org: float
    newbalance_orig: float
    name_dest: str
    oldbalance_dest: float
    newbalance_dest: float
    currency: str
    timestamp: datetime
    created_at: datetime


class RiskResultOut(BaseModel):
    model_config = ORM
    ml_model_used: str | None
    ml_fraud_score: float | None
    ml_prediction: int | None
    aml_score: float | None
    aml_risk_level: str | None
    rule_score: float | None
    behavior_score: float | None
    network_score: float | None
    triggered_rules: list[str] | None
    reasons: list[str] | None
    final_risk_score: float
    risk_level: str
    shap_available: bool
    investigation_summary: dict | None


class TransactionAnalysisOut(BaseModel):
    """What POST /transactions returns: the stored row plus its risk result."""
    transaction: TransactionOut
    risk: RiskResultOut
    alert_id: int | None = None
    notification: dict | None = None
    aml_explanation: str | None = None
    aml_explanation_details: dict | None = None

class ShapFeature(BaseModel):
    feature: str
    value: float
    shap_value: float
    direction: str


class ExplanationOut(BaseModel):
    transaction_id: int
    available: bool
    explainer_model: str | None = None
    base_value: float | None = None
    top_features: list[ShapFeature] = []
    error: str | None = None


# --- Alerts -----------------------------------------------------------------
class AlertOut(BaseModel):
    model_config = ORM
    id: int
    transaction_id: int
    risk_level: str
    final_risk_score: float
    message: str
    status: str
    created_at: datetime


class AlertStatusUpdate(BaseModel):
    status: str = Field(examples=["IN_REVIEW"])


# --- Cases ------------------------------------------------------------------
class CaseCreate(BaseModel):
    transaction_id: int
    title: str = Field(max_length=200, examples=["Large transfer review"])
    description: str | None = None
    priority: str = Field(default="MEDIUM", examples=["HIGH"])
    assigned_to_id: int | None = None


class CaseUpdate(BaseModel):
    status: str | None = Field(default=None, examples=["IN_PROGRESS"])
    priority: str | None = None
    assigned_to_id: int | None = None
    resolution: str | None = None


class CaseNoteCreate(BaseModel):
    note: str = Field(min_length=1, examples=["Contacted the customer for proof of funds."])


class CaseNoteOut(BaseModel):
    model_config = ORM
    id: int
    note: str
    author_id: int
    created_at: datetime


class CaseOut(BaseModel):
    model_config = ORM
    id: int
    case_ref: str
    title: str
    description: str | None
    transaction_id: int
    alert_id: int | None
    status: str
    priority: str
    resolution: str | None
    created_by_id: int
    assigned_to_id: int | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class CaseDetailOut(CaseOut):
    notes: list[CaseNoteOut] = []


# --- Audit and analytics ----------------------------------------------------
class AuditLogOut(BaseModel):
    model_config = ORM
    id: int
    username: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime


class AnalyticsSummary(BaseModel):
    total_transactions: int
    total_amount: float
    alerts_by_level: dict[str, int]
    open_alerts: int
    cases_by_status: dict[str, int]
    average_risk_score: float
    ml_flagged_count: int
