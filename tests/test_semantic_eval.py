"""Judge-eval harness — tested with deterministic fake judges (no LLM). Proves it surfaces a good
judge as 100% and a degenerate judge (always-abstain) as low recall."""
import json, os, unittest
from faithful_core.semantic_eval import run_entailment_eval, format_entailment_eval

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, "goldens", "semantic_gold.json")


def load_cases():
    with open(GOLD) as fh:
        return json.load(fh)["cases"]


class SemanticEval(unittest.TestCase):
    def test_perfect_judge_scores_full(self):
        cases = load_cases()
        by_claim = {c["claim"]: c["expected"] for c in cases}
        perfect = lambda claim, ev: {"verdict": by_claim[claim], "confidence": 0.9}
        r = run_entailment_eval(perfect, cases)
        self.assertEqual(r["accuracy"], 1.0)
        self.assertEqual(r["supported_recall"], 1.0)
        self.assertEqual(r["violated_precision"], 1.0)

    def test_always_abstain_surfaces_zero_recall(self):
        cases = load_cases()
        r = run_entailment_eval(lambda c, e: {"verdict": "abstain"}, cases)
        self.assertLess(r["accuracy"], 1.0)
        self.assertEqual(r["supported_recall"], 0.0)   # kept no supported claim
        self.assertIsNone(r["violated_precision"])     # flagged nothing → precision undefined

    def test_overeager_judge_has_low_violated_precision(self):
        # a judge that cries 'violated' on everything catches real violations but also drops genuine ones
        cases = load_cases()
        r = run_entailment_eval(lambda c, e: {"verdict": "violated"}, cases)
        n_violated = sum(1 for c in cases if c["expected"] == "violated")
        self.assertAlmostEqual(r["violated_precision"], n_violated / len(cases))

    def test_format(self):
        cases = load_cases()
        r = run_entailment_eval(lambda c, e: {"verdict": "abstain"}, cases)
        self.assertIn("Entailment judge eval", format_entailment_eval(r))


if __name__ == "__main__":
    unittest.main()
