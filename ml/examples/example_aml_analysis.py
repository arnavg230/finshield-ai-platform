import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from aml.aml_analysis import analyze_aml

history = [
    {"timestamp":"2022/08/01 10:00","sender_id":"C100","receiver_id":"C200","amount":5000},
    {"timestamp":"2022/08/02 10:00","sender_id":"C100","receiver_id":"C201","amount":6000},
    {"timestamp":"2022/08/03 10:00","sender_id":"C100","receiver_id":"C202","amount":5500},
    {"timestamp":"2022/08/04 10:00","sender_id":"C100","receiver_id":"C203","amount":4500},
]
transaction = {
    "timestamp":"2022/08/05 10:00","sender_id":"C100","receiver_id":"C999",
    "amount":150000,"currency":"US Dollar","payment_type":"ACH"
}
result = analyze_aml(transaction, history)
for key in ["aml_score","risk_level","triggered_rules","rule_score","behavior_score","network_score","reasons"]:
    print(f"{key}: {result[key]}")
print("investigation_summary:", result["investigation_summary"]["summary"])
print("notification:", result["notification"])
