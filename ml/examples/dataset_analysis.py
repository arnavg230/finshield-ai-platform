import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from collections import Counter
from aml.preprocessing import parse_laundering_attempts

path = Path(__file__).parents[1] / "data" / "amlsim_laundering_attempts.txt"
rows = parse_laundering_attempts(path.read_text(encoding="utf-8"))
print("Parsed transactions:", len(rows))
print("Laundering patterns:", len(Counter(r["laundering_pattern"] for r in rows)))
for name, count in Counter(r["laundering_pattern"] for r in rows).most_common(10):
    print(f"- {name}: {count}")
print("First parsed row:", rows[0] if rows else None)
