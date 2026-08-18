"""CongruenceCheck — emits attribution + overgeneralization findings from a 3-axis judge."""
import unittest
from fides import CongruenceCheck, abstaining_congruence_judge, surface_policy


def judge(on_subject, kind_ok, conf=0.9):
    def _j(claim_text, evidence_texts):
        return {"on_subject": on_subject, "kind_ok": kind_ok, "confidence": conf, "reason": "r"}
    return _j


def run(j, surface="compliance"):
    findings = CongruenceCheck(judge=j).run(
        [{"text": "Sitagliptin needs no renal dose adjustment", "evidence_texts": ["metformin label..."]}],
        {"surface": surface})
    return {f.dimension: f for f in findings}


class Congruence(unittest.TestCase):
    def test_emits_both_dimensions(self):
        f = run(judge("supported", "supported"))
        self.assertIn("attribution", f)
        self.assertIn("overgeneralization", f)
        self.assertEqual(f["attribution"].groundedness, "in_corpus")
        self.assertEqual(f["overgeneralization"].groundedness, "in_corpus")

    def test_misattribution_flagged_on_attribution_axis(self):
        # the sitagliptin case: right drug-class fact, WRONG drug → on_subject violated
        f = run(judge("violated", "supported"))
        self.assertEqual(f["attribution"].groundedness, "false")
        self.assertEqual(f["overgeneralization"].groundedness, "in_corpus")
        # llm_judge false → HOLD on compliance (never auto-drop)
        self.assertEqual(surface_policy(f["attribution"]), "hold")

    def test_overgeneralization_flagged_on_kind_axis(self):
        f = run(judge("supported", "violated"))
        self.assertEqual(f["overgeneralization"].groundedness, "false")

    def test_default_judge_abstains_on_both(self):
        f = run(abstaining_congruence_judge)
        self.assertEqual(f["attribution"].groundedness, "abstain")
        self.assertEqual(f["overgeneralization"].groundedness, "abstain")

    def test_failsafe_on_judge_error(self):
        def boom(a, b):
            raise ValueError("x")
        f = run(boom)
        self.assertEqual(f["attribution"].groundedness, "abstain")
        self.assertTrue(f["attribution"].reason.startswith("judge_error"))


if __name__ == "__main__":
    unittest.main()
