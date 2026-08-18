"""End-to-end: EntailmentCheck outputs → P/R matrix. Shows the honest semantic picture — an
llm_judge can't auto-drop, so on marketing a caught violation still ships (flag) = a measured
escape; and a judge MISS escapes on both tiers. This is why judges stay flag-only until calibrated."""
import unittest
from faithful_core import EntailmentCheck, run_gate_eval


def scripted(mapping):
    def _j(text, ev):
        return mapping[text]
    return _j


class SemanticHarness(unittest.TestCase):
    def setUp(self):
        check = EntailmentCheck(judge=scripted({
            "A": {"verdict": "supported", "confidence": 0.9, "reason": ""},   # true & judged supported
            "B": {"verdict": "violated", "confidence": 0.9, "reason": ""},    # false & judge CATCHES it
            "C": {"verdict": "supported", "confidence": 0.9, "reason": ""},   # false but judge MISSES it
        }))

        def span(text, truth):
            return {"id": text, "dimension": "entailment", "truth": truth,
                    "findings": check.run([{"text": text}], {"surface": "compliance"})}

        self.report = run_gate_eval([span("A", "in_corpus"), span("B", "false"), span("C", "false")])

    def cell(self, tier):
        return next(c for c in self.report["cells"] if c["dimension"] == "entailment" and c["tier"] == tier)

    def test_compliance_holds_caught_violation_but_misses_escape(self):
        # B (violated) → hold (withheld); C (judge miss) → keep → escape. So exactly 1 escape.
        self.assertEqual(self.cell("compliance")["escapes"], 1)

    def test_marketing_flags_ship_so_both_falses_escape(self):
        # B flagged→ships, C keeps→ships. Both truth-false → 2 escapes (the accepted-until-calibrated risk).
        self.assertEqual(self.cell("marketing")["escapes"], 2)

    def test_genuine_recall_preserved(self):
        # A is true and shipped on both tiers → no recall loss.
        self.assertEqual(self.cell("compliance")["recall_losses"], 0)
        self.assertEqual(self.cell("marketing")["recall_losses"], 0)


if __name__ == "__main__":
    unittest.main()
