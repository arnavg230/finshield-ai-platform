
"""Admin-only AML scenario testing endpoint."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import ROLE_ADMIN, Transaction
from app.routers.transactions import run_analysis

router = APIRouter(
    prefix="/api/admin/aml-testing",
    tags=["AML Testing"],
    dependencies=[Depends(require_roles(ROLE_ADMIN))],
)

BASE_TIME = datetime(2026, 10, 29, 10, 0)


def build_scenarios():
    """Build the 15 histories described in FinShield_AI_AML_15_Test_Scenarios."""
    cases = []

    def add(name, description, sender, receiver, amount, history=()):
        cases.append({"name": name, "description": description,
                      "sender": sender, "receiver": receiver,
                      "amount": amount, "history": list(history)})

    def prior(sender, receiver, amount, hours_ago):
        return {"sender": sender, "receiver": receiver, "amount": amount,
                "hours_ago": hours_ago}

    add("01 - Normal low-value transaction", "Low amount and no transaction history.", "SENDER_01", "RECEIVER_01", 500)
    add("02 - Just below high-amount threshold", "Checks the boundary immediately below $100,000.", "SENDER_02", "RECEIVER_02", 99999)
    add("03 - At high-amount threshold", "Checks high amount and new receiver at $100,000.", "SENDER_03", "RECEIVER_03", 100000)
    add("04 - New receiver below threshold", "$49,999 compared with two approximately $30,000 historical transfers.", "SENDER_04", "RECEIVER_04", 49999,
        [prior("SENDER_04", "OTHER_04A", 30000, 48), prior("SENDER_04", "OTHER_04B", 30000, 72)])
    add("05 - Large transfer to a new receiver", "New receiver and amount spike against a much lower average.", "SENDER_05", "RECEIVER_05", 60000,
        [prior("SENDER_05", "OTHER_05A", 10000, 48), prior("SENDER_05", "OTHER_05B", 10000, 72)])
    add("06 - Four transactions within 24 hours", "Three historical transactions plus current transaction.", "SENDER_06", "RECEIVER_06", 1000,
        [prior("SENDER_06", "R06A", 1000, 2), prior("SENDER_06", "R06B", 1000, 5), prior("SENDER_06", "R06C", 1000, 8)])
    add("07 - Five transactions within 24 hours", "Four historical transactions plus current transaction.", "SENDER_07", "RECEIVER_07", 1000,
        [prior("SENDER_07", f"R07_{i}", 1000, 2 + i * 3) for i in range(4)])
    add("08 - Behaviour ratio 2x", "Current amount is twice the $1,000 historical average.", "SENDER_08", "RECEIVER_08", 2000,
        [prior("SENDER_08", "OLD_08", 1000, 48)])
    add("09 - Behaviour ratio 3x", "Current amount is three times the $1,000 historical average.", "SENDER_09", "RECEIVER_09", 3000,
        [prior("SENDER_09", "OLD_09", 1000, 48)])
    add("10 - Behaviour ratio 5x", "Current amount is five times the $1,000 historical average.", "SENDER_10", "RECEIVER_10", 5000,
        [prior("SENDER_10", "OLD_10", 1000, 48)])
    add("11 - Sender connected to multiple receivers", "Six receivers; history is outside the 24-hour frequency window.", "SENDER_11", "RECEIVER_11_NEW", 2000,
        [prior("SENDER_11", f"R11_{i}", 1000, 48 + 24 * i) for i in range(5)])
    add("12 - Receiver connected to multiple senders", "Five other senders plus current transfer to the same receiver.", "SENDER_12", "RECEIVER_12", 2000,
        [prior(f"OTHER_12_{i}", "RECEIVER_12", 1000, 48 + 24 * i) for i in range(5)])
    add("13 - Reciprocal transaction", "History contains the reverse direction of the current transfer.", "SENDER_13", "RECEIVER_13", 5000,
        [prior("RECEIVER_13", "SENDER_13", 5000, 48)])
    add("14 - Combined high-risk indicators", "High amount, frequency, new receiver, spike, and network activity.", "SENDER_14", "RECEIVER_14_NEW", 150000,
        [prior("SENDER_14", f"R14_{i}", 1000, 2 + 2 * i) for i in range(5)])
    add("15 - Stable customer activity", "Ten stable historical transfers spread over more than 24 hours.", "SENDER_15", "RECEIVER_15", 1000,
        [prior("SENDER_15", "RECEIVER_15", 1000, 48 + 24 * i) for i in range(10)])
    return cases


SCENARIOS = build_scenarios()


def create_transaction(scenario, receiver, amount, timestamp, step, sender=None):
    sender_balance = max(amount * 10, 1000000)

    return Transaction(
        txn_ref=f"AMLTEST-{uuid.uuid4().hex[:12].upper()}",
        step=step,
        txn_type="TRANSFER",
        amount=float(amount),
        name_orig=sender or scenario["sender"],
        oldbalance_org=float(sender_balance),
        newbalance_orig=float(sender_balance - amount),
        name_dest=receiver,
        oldbalance_dest=0.0,
        newbalance_dest=float(amount),
        is_flagged_fraud=0,
        currency="US Dollar",
        timestamp=timestamp,
        submitted_by_id=None,
    )


@router.post("/run")
def run_aml_scenarios(db: Session = Depends(get_db)):
    """Run all 15 AML scenarios and roll back their database records."""

    results = []
    savepoint = None

    try:
        savepoint = db.begin_nested()
        base_time = BASE_TIME

        for scenario_index, scenario in enumerate(SCENARIOS):
            test_time = base_time + timedelta(minutes=scenario_index * 10)

            for history_index, item in enumerate(scenario["history"]):
                history_time = test_time - timedelta(hours=item["hours_ago"])

                historical = create_transaction(
                    scenario,
                    item["receiver"],
                    item["amount"],
                    history_time,
                    history_index + 1,
                    sender=item["sender"],
                )
                db.add(historical)

            db.flush()

            target = create_transaction(
                scenario,
                scenario["receiver"],
                scenario["amount"],
                test_time,
                10 + scenario_index,
            )
            db.add(target)
            db.flush()

            risk, extras = run_analysis(db, target, commit=False)

            results.append({
                "scenario": scenario["name"],
                "description": scenario["description"],
                "transaction": {
                    "amount": target.amount,
                    "sender": target.name_orig,
                    "receiver": target.name_dest,
                },
                "ml_score": risk.ml_fraud_score,
                "ml_prediction": risk.ml_prediction,
                "aml_score": risk.aml_score,
                "aml_risk_level": risk.aml_risk_level,
                "hybrid_score": risk.final_risk_score,
                "hybrid_risk_level": risk.risk_level,
                "rule_score": risk.rule_score,
                "behavior_score": risk.behavior_score,
                "network_score": risk.network_score,
                "triggered_rules": risk.triggered_rules or [],
                "reasons": risk.reasons or [],
                "investigation_summary": risk.investigation_summary,
                "aml_explanation": extras.get("aml_explanation"),
            })

        # Undo all test inserts, risk results and alerts.
        savepoint.rollback()
        db.expire_all()

        return {
            "message": "AML scenarios completed. Test records were rolled back.",
            "scenarios_run": len(results),
            "test_data_saved": False,
            "results": results,
        }

    except Exception as exc:
        if savepoint is not None and savepoint.is_active:
            savepoint.rollback()
        db.expire_all()
        raise HTTPException(
            status_code=500,
            detail=f"AML scenario testing failed: {str(exc)}",
        ) from exc
