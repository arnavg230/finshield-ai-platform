import sys
from pathlib import Path
import unittest

ML_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(ML_DIR))

from src.analysis_aml import analyze_aml
from src.preprocessing_aml import parse_laundering_attempts


class AMLTests(unittest.TestCase):
    def test_high_amount_rule(self):
        tx = {
            "timestamp": "2022/08/05 10:00",
            "sender_id": "A",
            "receiver_id": "B",
            "amount": 200000
        }
        result = analyze_aml(tx, [])
        self.assertIn("HIGH_AMOUNT", result["triggered_rules"])

    def test_parser(self):
        text = """BEGIN LAUNDERING ATTEMPT - STACK
2022/08/09 05:14,A,AA,B,BB,5331.44,US Dollar,5331.44,US Dollar,ACH,1
END LAUNDERING ATTEMPT - STACK"""
        rows = parse_laundering_attempts(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["laundering_pattern"], "LAUNDERING ATTEMPT - STACK")

    def test_score_range(self):
        tx = {
            "timestamp": "2022/08/05 10:00",
            "sender_id": "A",
            "receiver_id": "B",
            "amount": 1000
        }
        result = analyze_aml(tx, [])
        self.assertGreaterEqual(result["aml_score"], 0)
        self.assertLessEqual(result["aml_score"], 1)


if __name__ == "__main__":
    unittest.main()