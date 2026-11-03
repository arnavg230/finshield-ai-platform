"""Database tables for FinShield AI."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------------------------------------------------------------------------
# Roles used by the RBAC checks. Kept as plain strings so they are easy to read
# in the database and easy to explain.
# ---------------------------------------------------------------------------
ROLE_CUSTOMER = "CUSTOMER"
ROLE_ANALYST = "ANALYST"
ROLE_COMPLIANCE = "COMPLIANCE"
ROLE_ADMIN = "ADMIN"
ALL_ROLES = [ROLE_CUSTOMER, ROLE_ANALYST, ROLE_COMPLIANCE, ROLE_ADMIN]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    full_name = Column(String(120), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=ROLE_CUSTOMER)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transactions = relationship("Transaction", back_populates="submitted_by")


class Transaction(Base):
    """
    One financial transaction.

    The PaySim style columns (step, type, balances) are what Member 2's model
    needs. The sender/receiver columns are what Member 4's AML module needs.
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    txn_ref = Column(String(40), unique=True, nullable=False, index=True)

    step = Column(Integer, nullable=False, default=1)
    txn_type = Column(String(20), nullable=False)          # PaySim: TRANSFER, CASH_OUT, ...
    amount = Column(Float, nullable=False)

    name_orig = Column(String(50), nullable=False, index=True)   # sender
    oldbalance_org = Column(Float, nullable=False, default=0.0)
    newbalance_orig = Column(Float, nullable=False, default=0.0)

    name_dest = Column(String(50), nullable=False, index=True)   # receiver
    oldbalance_dest = Column(Float, nullable=False, default=0.0)
    newbalance_dest = Column(Float, nullable=False, default=0.0)

    is_flagged_fraud = Column(Integer, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="US Dollar")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    submitted_by = relationship("User", back_populates="transactions")
    risk_result = relationship(
        "RiskResult", back_populates="transaction", uselist=False,
        cascade="all, delete-orphan",
    )
    alert = relationship(
        "Alert", back_populates="transaction", uselist=False,
        cascade="all, delete-orphan",
    )


class RiskResult(Base):
    """Output of the ML model, the AML module and the hybrid combination."""

    __tablename__ = "risk_results"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(
        Integer, ForeignKey("transactions.id"), unique=True, nullable=False
    )

    # Member 2 (ML)
    ml_model_used = Column(String(40), nullable=True)
    ml_fraud_score = Column(Float, nullable=True)
    ml_prediction = Column(Integer, nullable=True)          # 0 = normal, 1 = fraud
    shap_available = Column(Boolean, default=False, nullable=False)
    shap_base_value = Column(Float, nullable=True)
    shap_top_features = Column(JSON, nullable=True)

    # Member 4 (AML)
    aml_score = Column(Float, nullable=True)
    aml_risk_level = Column(String(10), nullable=True)
    rule_score = Column(Float, nullable=True)
    behavior_score = Column(Float, nullable=True)
    network_score = Column(Float, nullable=True)
    triggered_rules = Column(JSON, nullable=True)
    reasons = Column(JSON, nullable=True)
    investigation_summary = Column(JSON, nullable=True)

    # Hybrid (Member 1)
    final_risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(10), nullable=False, default="LOW")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transaction = relationship("Transaction", back_populates="risk_result")


class Alert(Base):
    """Created automatically when a transaction is not LOW risk."""

    __tablename__ = "alerts"

    ALERT_OPEN = "OPEN"
    ALERT_IN_REVIEW = "IN_REVIEW"
    ALERT_CLOSED = "CLOSED"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(
        Integer, ForeignKey("transactions.id"), unique=True, nullable=False
    )
    risk_level = Column(String(10), nullable=False)
    final_risk_score = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default=ALERT_OPEN)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    transaction = relationship("Transaction", back_populates="alert")
    case = relationship("Case", back_populates="alert", uselist=False)


class Case(Base):
    """Investigation case opened by an analyst on top of an alert."""

    __tablename__ = "cases"

    STATUS_OPEN = "OPEN"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_CLOSED = "CLOSED"
    ALL_STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_CLOSED]

    id = Column(Integer, primary_key=True, index=True)
    case_ref = Column(String(40), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)

    status = Column(String(20), nullable=False, default=STATUS_OPEN)
    priority = Column(String(10), nullable=False, default="MEDIUM")
    resolution = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    closed_at = Column(DateTime, nullable=True)

    alert = relationship("Alert", back_populates="case")
    transaction = relationship("Transaction")
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    notes = relationship(
        "CaseNote", back_populates="case", cascade="all, delete-orphan"
    )


class CaseNote(Base):
    __tablename__ = "case_notes"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    case = relationship("Case", back_populates="notes")
    author = relationship("User")


class AuditLog(Base):
    """Record of important actions, required for the audit trail use case."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), nullable=True)
    action = Column(String(60), nullable=False, index=True)
    entity_type = Column(String(40), nullable=True)
    entity_id = Column(String(40), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")
