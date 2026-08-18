"""The falsifiable platform test: the Python numeric ledger must reproduce the CANONICAL TS verdicts
byte-for-byte. If these golden vectors don't match, the 'portable core' premise is dead."""
import json, os, unittest
from fides.numeric import ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, "goldens", "numeric_golden.json")


class NumericConformance(unittest.TestCase):
    def test_ts_python_parity(self):
        data = json.load(open(GOLD))
        self.assertGreaterEqual(len(data["cases"]), 20)
        for c in data["cases"]:
            facts = {g["id"]: ledger.materialize_fact(g) for g in c["input"]["facts"]}
            claim = ledger.materialize_claim(c["input"]["claim"])
            got = ledger.verify_claim(claim, facts, c["input"].get("opts") or {})
            exp = c["expected"]
            self.assertEqual(
                (got["ok"], got["code"]), (exp["ok"], exp["code"]),
                "%s: expected %s/%s got %s/%s" % (c["id"], exp["ok"], exp["code"], got["ok"], got["code"]),
            )


if __name__ == "__main__":
    unittest.main()
