import sys
import json
from pathlib import Path

# Add the ML directory to Python's import path
ML_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ML_DIR))

from src.analysis_aml import analyze_aml
from src.explanation_aml import generate_detailed_aml_explanation


# --------------------------------------------------
# Helper function to create transactions
# --------------------------------------------------

def create_transaction(
    sender,
    receiver,
    amount,
    timestamp="2026/10/29 10:00",
    payment_type="TRANSFER"
):
    return {
        "timestamp": timestamp,
        "sender_id": sender,
        "sender_account": sender,
        "receiver_id": receiver,
        "receiver_account": receiver,
        "amount": amount,
        "currency": "USD",
        "payment_type": payment_type
    }


# --------------------------------------------------
# Test scenarios
# --------------------------------------------------

scenarios = [

    {
        "name": "Scenario 1: Normal Transaction",
        "transaction": create_transaction(
            "S1", "R1", 500
        ),
        "history": []
    },

    {
        "name": "Scenario 2: High-Value Transaction",
        "transaction": create_transaction(
            "S2", "R2", 150000
        ),
        "history": []
    },

    {
        "name": "Scenario 3: New Receiver",
        "transaction": create_transaction(
            "S3", "R_NEW", 60000
        ),
        "history": [
            create_transaction(
                "S3", "R_OLD1", 1000,
                "2026/10/29 08:00"
            ),
            create_transaction(
                "S3", "R_OLD2", 2000,
                "2026/10/29 09:00"
            )
        ]
    },

    {
        "name": "Scenario 4: Repeated Transactions",
        "transaction": create_transaction(
            "S4", "R4", 1000,
            "2026/10/29 10:00"
        ),
        "history": [
            create_transaction(
                "S4", "R4", 900,
                "2026/10/29 09:50"
            ),
            create_transaction(
                "S4", "R4", 800,
                "2026/10/29 09:40"
            ),
            create_transaction(
                "S4", "R4", 700,
                "2026/10/29 09:30"
            ),
            create_transaction(
                "S4", "R4", 600,
                "2026/10/29 09:20"
            ),
            create_transaction(
                "S4", "R4", 500,
                "2026/10/29 09:10"
            )
        ]
    },

    {
        "name": "Scenario 5: Multiple Receivers",
        "transaction": create_transaction(
            "S5", "R_NEW5", 2000,
            "2026/10/29 10:00"
        ),
        "history": [
            create_transaction(
                "S5", "R10", 1000,
                "2026/10/29 09:50"
            ),
            create_transaction(
                "S5", "R11", 1200,
                "2026/10/29 09:40"
            ),
            create_transaction(
                "S5", "R12", 1500,
                "2026/10/29 09:30"
            ),
            create_transaction(
                "S5", "R13", 1800,
                "2026/10/29 09:20"
            ),
            create_transaction(
                "S5", "R14", 2000,
                "2026/10/29 09:10"
            )
        ]
    }
]


# --------------------------------------------------
# Run AML analysis and explanation
# --------------------------------------------------

def run_tests():

    print("\n" + "=" * 65)
    print("FINSHIELD AI - AML SCENARIO TESTING")
    print("=" * 65)

    for scenario in scenarios:

        name = scenario["name"]
        transaction = scenario["transaction"]
        history = scenario["history"]

        print("\n" + "-" * 65)
        print(name)
        print("-" * 65)

        try:

            # Run AML analysis
            result = analyze_aml(transaction, history)

            # Generate detailed explanation
            explanation = generate_detailed_aml_explanation(
                transaction_data=transaction,
                transaction_history=history,
                analysis_result=result
            )

            # Display transaction information
            print("Sender:", transaction["sender_id"])
            print("Receiver:", transaction["receiver_id"])
            print("Amount:", transaction["amount"])
            print("History size:", len(history))

            # Display AML results
            print("\nAML Score:", result.get("aml_score"))
            print("Risk Level:", result.get("risk_level"))
            print("Rule Score:", result.get("rule_score"))
            print("Behavior Score:", result.get("behavior_score"))
            print("Network Score:", result.get("network_score"))

            print("\nTriggered Rules:")
            print(json.dumps(
                result.get("triggered_rules", []),
                indent=4,
                default=str
            ))

            print("\nReasons:")
            print(json.dumps(
                result.get("reasons", []),
                indent=4,
                default=str
            ))

            print("\nDetailed Explanation:")
            print(explanation)

            print("\nTEST RESULT: PASS")

        except Exception as e:

            print("\nTEST RESULT: FAIL")
            print("Error:", str(e))

    print("\n" + "=" * 65)
    print("AML SCENARIO TESTING COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()