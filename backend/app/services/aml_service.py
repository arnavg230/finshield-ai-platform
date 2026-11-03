# """
# Wrapper around Member 4's AML package.

# Member 4's code is imported as-is from the `member4_aml` folder. The only work
# done here is translating between my database columns and the field names their
# `analyze_aml()` function expects, and formatting timestamps as "%Y/%m/%d %H:%M"
# because that is the only format their rule engine parses.
# """
# import sys

# from app.config import AML_HISTORY_LIMIT, AML_PACKAGE_DIR

# from pathlib import Path
# import importlib.util

# # Make Member 4's package importable without copying their code into my folder.
# if str(AML_PACKAGE_DIR) not in sys.path:
#     sys.path.insert(0, str(AML_PACKAGE_DIR))

# try:
#     from aml.aml_analysis import analyze_aml           # Member 4's entry point
#     from aml.rules import DEFAULT_THRESHOLDS           # shown on the admin screen
#     from aml.explanation_aml import generate_detailed_aml_explanation

#     AML_AVAILABLE = True
#     AML_IMPORT_ERROR = None
# except Exception as exc:                               # noqa: BLE001
#     analyze_aml = None
#     generate_detailed_aml_explanation = None
#     DEFAULT_THRESHOLDS = {}
#     AML_AVAILABLE = False
#     AML_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

# # Member 4's rules.py parses timestamps with this format only.
# AML_TIME_FORMAT = "%Y/%m/%d %H:%M"


# def to_aml_dict(transaction) -> dict:
#     """Convert a Transaction row into the dict shape Member 4 documented."""
#     return {
#         "timestamp": transaction.timestamp.strftime(AML_TIME_FORMAT),
#         "sender_id": transaction.name_orig,
#         "sender_account": transaction.name_orig,
#         "receiver_id": transaction.name_dest,
#         "receiver_account": transaction.name_dest,
#         "amount": float(transaction.amount),
#         "currency": transaction.currency,
#         "payment_type": transaction.txn_type,
#     }


# def get_history(db, transaction) -> list[dict]:
#     """
#     Past transactions of the same sender, newest first.

#     Member 4's rules, behaviour and network analysis all need this history;
#     without it every transaction looks like a first-time customer.
#     """
#     from app.models import Transaction

#     rows = (
#         db.query(Transaction)
#         .filter(
#             Transaction.name_orig == transaction.name_orig,
#             Transaction.id != transaction.id,
#             Transaction.timestamp <= transaction.timestamp,
#         )
#         .order_by(Transaction.timestamp.desc())
#         .limit(AML_HISTORY_LIMIT)
#         .all()
#     )
#     return [to_aml_dict(row) for row in rows]


# # def analyze(db, transaction) -> dict:
# #     """Run Member 4's AML analysis on one stored transaction."""
# #     if not AML_AVAILABLE:
# #         return {"available": False, "error": AML_IMPORT_ERROR}

# #     history = get_history(db, transaction)
# #     try:
# #         result = analyze_aml(to_aml_dict(transaction), history)
# #         result["available"] = True
# #         result["history_size"] = len(history)
# #         return result
# #     except Exception as exc:                           # noqa: BLE001
# #         return {"available": False, "error": f"{type(exc).__name__}: {exc}"}

# def analyze(db, transaction) -> dict:
#     """Run AML analysis and generate a detailed explanation."""
#     if not AML_AVAILABLE:
#         return {"available": False, "error": AML_IMPORT_ERROR}

#     history = get_history(db, transaction)
#     transaction_data = to_aml_dict(transaction)

#     try:
#         result = analyze_aml(transaction_data, history)

#         result["available"] = True
#         result["history_size"] = len(history)

#         if generate_detailed_aml_explanation is not None:
#             detailed = generate_detailed_aml_explanation(
#                 transaction_data=transaction_data,
#                 transaction_history=history,
#                 analysis_result=result,
#             )
#             result["detailed_explanation"] = detailed["explanation"]
#             result["explanation_details"] = detailed

#         return result

#     except Exception as exc:
#         return {
#             "available": False,
#             "error": f"{type(exc).__name__}: {exc}",
#         }


# def get_thresholds() -> dict:
#     """Current rule thresholds, so an admin can see what the engine uses."""
#     return dict(DEFAULT_THRESHOLDS)



"""
AML service for FinShield AI.

Integrates the existing AML analysis modules from code/ml/src with the
FastAPI backend and attaches detailed explanations when available.
"""

import sys
from pathlib import Path

from app.config import AML_HISTORY_LIMIT, REPO_ROOT


# -------------------------------------------------------------------
# 1. Locate and import the existing AML modules
# -------------------------------------------------------------------

ML_DIR = REPO_ROOT / "ml"

if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

try:
    from src.analysis_aml import analyze_aml
    from src.rules_aml import DEFAULT_THRESHOLDS

    AML_AVAILABLE = True
    AML_IMPORT_ERROR = None

except Exception as exc:
    analyze_aml = None
    DEFAULT_THRESHOLDS = {}
    AML_AVAILABLE = False
    AML_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


# -------------------------------------------------------------------
# 2. Import the detailed AML explanation module
# -------------------------------------------------------------------

generate_detailed_aml_explanation = None
EXPLANATION_IMPORT_ERROR = None

try:
    explanation_file = ML_DIR / "src" / "explanation_aml.py"

    if not explanation_file.is_file():
        raise FileNotFoundError(
            f"Explanation module not found: {explanation_file}"
        )

    from src.explanation_aml import generate_detailed_aml_explanation

except Exception as exc:
    EXPLANATION_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


# Timestamp format expected by the AML modules
AML_TIME_FORMAT = "%Y/%m/%d %H:%M"


# -------------------------------------------------------------------
# 3. Convert a database transaction into the AML input format
# -------------------------------------------------------------------

def to_aml_dict(transaction) -> dict:
    """Convert a database Transaction row to the AML input format."""
    return {
        "timestamp": transaction.timestamp.strftime(AML_TIME_FORMAT),
        "sender_id": transaction.name_orig,
        "sender_account": transaction.name_orig,
        "receiver_id": transaction.name_dest,
        "receiver_account": transaction.name_dest,
        "amount": float(transaction.amount),
        "currency": transaction.currency,
        "payment_type": transaction.txn_type,
    }


# -------------------------------------------------------------------
# 4. Retrieve prior sender and receiver relationships
# -------------------------------------------------------------------

def get_history(db, transaction) -> list[dict]:
    """Get prior transactions linked to this sender or receiver.

    Rules and behaviour filter this list to the current sender themselves;
    network analysis also needs incoming, outgoing, and reciprocal edges for
    both accounts involved in the current transaction.
    """
    from sqlalchemy import or_
    from app.models import Transaction

    rows = (
        db.query(Transaction)
        .filter(
            or_(
                Transaction.name_orig == transaction.name_orig,
                Transaction.name_dest == transaction.name_orig,
                Transaction.name_orig == transaction.name_dest,
                Transaction.name_dest == transaction.name_dest,
            ),
            Transaction.id != transaction.id,
            Transaction.timestamp <= transaction.timestamp,
        )
        .order_by(Transaction.timestamp.desc())
        .limit(AML_HISTORY_LIMIT)
        .all()
    )

    return [to_aml_dict(row) for row in rows]


# -------------------------------------------------------------------
# 5. Analyze the transaction and attach a detailed explanation
# -------------------------------------------------------------------

def analyze(db, transaction) -> dict:
    """
    Run the existing AML analysis and attach a detailed explanation.

    The original AML result is retained if explanation generation fails.
    """
    if not AML_AVAILABLE:
        return {
            "available": False,
            "error": AML_IMPORT_ERROR,
        }

    history = get_history(db, transaction)
    transaction_data = to_aml_dict(transaction)

    try:
        # Run the existing rules, behavior, network, scoring,
        # investigation-summary, and notification modules.
        result = analyze_aml(transaction_data, history)

        if not isinstance(result, dict):
            raise TypeError("analyze_aml() must return a dictionary.")

        result["available"] = True
        result["history_size"] = len(history)

        # Add the detailed explanation without changing the original score.
        if generate_detailed_aml_explanation is not None:
            try:
                detailed = generate_detailed_aml_explanation(
                    transaction_data=transaction_data,
                    transaction_history=history,
                    analysis_result=result,
                )

                if isinstance(detailed, dict):
                    result["detailed_explanation"] = detailed.get(
                        "explanation",
                        "No detailed explanation was generated.",
                    )
                    result["explanation_details"] = detailed
                else:
                    result["explanation_error"] = (
                        "The explanation function did not return a dictionary."
                    )

            except Exception as exc:
                result["explanation_error"] = (
                    f"{type(exc).__name__}: {exc}"
                )
        else:
            result["explanation_error"] = EXPLANATION_IMPORT_ERROR

        return result

    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


# -------------------------------------------------------------------
# 6. Return AML rule thresholds
# -------------------------------------------------------------------

def get_thresholds() -> dict:
    """Return the default thresholds used by the AML rule engine."""
    return dict(DEFAULT_THRESHOLDS)
