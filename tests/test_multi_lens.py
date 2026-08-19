"""make_multi_lens_judge: combination logic + a deterministic P/R harness A/B that PROVES why
'unanimous' is the escape-safe default (and why 'any' is opt-in). No LLM — a scripted base judge."""
import unittest
from fides import make_multi_lens_judge, EntailmentCheck, run_gate_eval

LENSES = ["LITERAL", "ADVERSARIAL", "SCOPE"]

# per-(case, lens) scripted verdicts. A plain (unframed) call = single-pass = the LITERAL framing.
SCRIPT = {
    # a fabrication the LITERAL framing rubber-stamps, that only ADVERSARIAL catches
    ("fab_caught", "LITERAL"): "supported", ("fab_caught", "ADVERSARIAL"): "violated", ("fab_caught", "SCOPE"): "abstain",
    # a fabrication no lens outright 'violates' — LITERAL supports, others abstain (the sneaky one)
    ("fab_sneaky", "LITERAL"): "supported", ("fab_sneaky", "ADVERSARIAL"): "abstain", ("fab_sneaky", "SCOPE"): "abstain",
    # a genuine claim the LITERAL framing wrongly abstains on; SCOPE recovers it
    ("genuine_missed", "LITERAL"): "abstain", ("genuine_missed", "ADVERSARIAL"): "abstain", ("genuine_missed", "SCOPE"): "supported",
    # a clean genuine claim every lens supports
    ("clean_true", "LITERAL"): "supported", ("clean_true", "ADVERSARIAL"): "supported", ("clean_true", "SCOPE"): "supported",
}


def base_judge(claim_or_framed, evidence):
    case = next(c for c in ("fab_caught", "fab_sneaky", "genuine_missed", "clean_true") if c in claim_or_framed)
    lens = next((L for L in LENSES if L in claim_or_framed), "LITERAL")  # unframed → single-pass = LITERAL
    return {"verdict": SCRIPT[(case, lens)], "confidence": 0.9}


class Combination(unittest.TestCase):
    def _m(self, survival):
        return make_multi_lens_judge(base_judge, LENSES, survival)

    def test_any_violation_wins_regardless_of_rule(self):
        for rule in ("unanimous", "majority", "any"):
            self.assertEqual(self._m(rule)("fab_caught", [])["verdict"], "violated")

    def test_unanimous_requires_all_supported(self):
        self.assertEqual(self._m("unanimous")("clean_true", [])["verdict"], "supported")
        self.assertEqual(self._m("unanimous")("genuine_missed", [])["verdict"], "abstain")  # 2 abstain → not unanimous
        self.assertEqual(self._m("unanimous")("fab_sneaky", [])["verdict"], "abstain")       # withheld, not supported

    def test_any_recovers_a_lone_supported(self):
        self.assertEqual(self._m("any")("genuine_missed", [])["verdict"], "supported")       # SCOPE lens rescues it
        self.assertEqual(self._m("any")("fab_sneaky", [])["verdict"], "supported")           # ...but also lets the fab through

    def test_per_lens_verdicts_surfaced(self):
        r = self._m("unanimous")("fab_caught", [])
        self.assertEqual(r["lens_verdicts"], ["supported", "violated", "abstain"])
        self.assertIn("L2=violated", r["reason"])


class HarnessAB(unittest.TestCase):
    """Score single-pass vs multi-lens through the real P/R harness on labeled gold, per the
    ship-gate: escape must stay 0 (fabrication invariant) while recall is not sacrificed."""

    CASES = [  # (id, claim, truth)
        ("fab_sneaky", "fab_sneaky", "false"),        # fabrication family
        ("genuine_missed", "genuine_missed", "in_corpus"),  # genuine family (single-pass abstains)
        ("clean_true", "clean_true", "in_corpus"),          # genuine family (all agree)
    ]

    def _eval(self, judge):
        chk = EntailmentCheck(judge=judge)
        spans = []
        for cid, claim, truth in self.CASES:
            findings = chk.run([{"text": claim, "evidence_texts": []}], {"surface": "compliance"})
            spans.append({"id": cid, "dimension": "entailment", "truth": truth, "findings": findings})
        return run_gate_eval(spans)

    def _cell(self, report):
        c = next(c for c in report["cells"] if c["dimension"] == "entailment" and c["tier"] == "compliance")
        recall = (c["should_publish"] - c["recall_losses"]) / c["should_publish"] if c["should_publish"] else 1.0
        return c["escapes"], recall

    def test_ab_single_vs_unanimous_vs_any(self):
        single_e, single_r = self._cell(self._eval(base_judge))  # single pass = LITERAL
        uni_e, uni_r = self._cell(self._eval(make_multi_lens_judge(base_judge, LENSES, "unanimous")))
        any_e, any_r = self._cell(self._eval(make_multi_lens_judge(base_judge, LENSES, "any")))

        # single-pass rubber-stamps the sneaky fabrication → it escapes
        self.assertGreaterEqual(single_e, 1)
        # UNANIMOUS drives fabrication-escape to ZERO (the ship-gate) ...
        self.assertEqual(uni_e, 0)
        # ... 'any' recovers genuine recall but REINTRODUCES the escape (why it's opt-in)
        self.assertGreater(any_r, uni_r)
        self.assertGreaterEqual(any_e, 1)


if __name__ == "__main__":
    unittest.main()
