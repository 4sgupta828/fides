"""P/R matrix: deterministic numeric never escapes; an llm-judge miss surfaces as an escape."""
import unittest
from fides.finding import Finding, ContentSpan
from fides.harness import run_gate_eval, wilson


def finding(dim, kind, groundedness):
    return Finding(check_id="c", dimension=dim, kind=kind,
                   span=ContentSpan("x", "compliance"), groundedness=groundedness, severity="high")


class Harness(unittest.TestCase):
    def setUp(self):
        self.spans = [
            {"id": "n1", "dimension": "numeric", "truth": "in_corpus",
             "findings": [finding("numeric", "deterministic", "in_corpus")]},
            {"id": "n2", "dimension": "numeric", "truth": "false",
             "findings": [finding("numeric", "deterministic", "false")]},
            # judge MISS: truth is a fabrication, judge said supported → an escape the harness catches
            {"id": "m1", "dimension": "misinterpretation", "truth": "false",
             "findings": [finding("misinterpretation", "llm_judge", "in_corpus")]},
        ]
        self.report = run_gate_eval(self.spans)

    def cell(self, dim, tier):
        return next(c for c in self.report["cells"] if c["dimension"] == dim and c["tier"] == tier)

    def test_numeric_zero_escapes(self):
        self.assertEqual(self.cell("numeric", "compliance")["escapes"], 0)
        self.assertEqual(self.cell("numeric", "marketing")["escapes"], 0)

    def test_judge_miss_is_caught_as_escape(self):
        self.assertGreater(self.cell("misinterpretation", "compliance")["escapes"], 0)

    def test_wilson_ci_no_over_certifying(self):
        w = wilson(0, 1)  # 0 escapes in 1 sample
        self.assertEqual(w["p"], 0.0)
        self.assertGreater(w["hi"], 0.5)  # cannot claim safety from n=1

    def test_wilson_zero_n(self):
        self.assertEqual(wilson(0, 0), {"p": 0.0, "lo": 0.0, "hi": 0.0})


if __name__ == "__main__":
    unittest.main()
