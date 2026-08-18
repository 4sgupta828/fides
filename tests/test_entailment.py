"""Entailment Check — injectable judge, fail-safe, and the llm_judge policy (never auto-drops)."""
import unittest
from fides import EntailmentCheck, abstaining_judge, surface_policy, compose_decision, is_published
from fides.finding import ContentSpan


def judge_supported(claim_text, evidence_texts):
    return {"verdict": "supported", "confidence": 0.9, "reason": "evidence supports the claim"}


def judge_violated(claim_text, evidence_texts):
    return {"verdict": "violated", "confidence": 0.9, "reason": "evidence contradicts the claim"}


def judge_lowconf(claim_text, evidence_texts):
    return {"verdict": "supported", "confidence": 0.3, "reason": "weak"}


def judge_malformed(claim_text, evidence_texts):
    return {"verdict": "yolo"}  # not a valid verdict


def judge_raises(claim_text, evidence_texts):
    raise RuntimeError("api down")


def _run(judge, surface="compliance", min_conf=0.0):
    check = EntailmentCheck(judge=judge, min_confidence=min_conf)
    return check.run([{"text": "Fund A beat its benchmark", "evidence_texts": ["Fund A returned 12%"]}],
                     {"surface": surface})[0]


class Entailment(unittest.TestCase):
    def test_supported_is_in_corpus_and_keeps(self):
        f = _run(judge_supported)
        self.assertEqual(f.groundedness, "in_corpus")
        self.assertEqual(f.kind, "llm_judge")
        self.assertEqual(surface_policy(f), "keep")

    def test_violated_never_auto_drops(self):
        # llm_judge false HOLDS on compliance (human review), FLAGS on marketing — never auto-drop.
        f_comp = _run(judge_violated, "compliance")
        self.assertEqual(f_comp.groundedness, "false")
        self.assertEqual(surface_policy(f_comp), "hold")
        f_mkt = _run(judge_violated, "marketing")
        self.assertEqual(surface_policy(f_mkt), "flag")

    def test_default_judge_abstains(self):
        f = _run(abstaining_judge)
        self.assertEqual(f.groundedness, "abstain")  # nothing ships as verified without a real judge
        self.assertEqual(surface_policy(f), "hold")   # compliance

    def test_low_confidence_becomes_abstain(self):
        f = _run(judge_lowconf, min_conf=0.6)
        self.assertEqual(f.groundedness, "abstain")   # below floor → abstain, not a confident pass

    def test_malformed_verdict_is_abstain(self):
        self.assertEqual(_run(judge_malformed).groundedness, "abstain")

    def test_judge_error_is_failsafe_abstain(self):
        f = _run(judge_raises)
        self.assertEqual(f.groundedness, "abstain")
        self.assertTrue(f.reason.startswith("judge_error"))


if __name__ == "__main__":
    unittest.main()
