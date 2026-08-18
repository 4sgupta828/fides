"""Anti-slop: deterministic detection, the Gate's advisory slop report (separate from faithfulness),
and the generation de-slop pass (subordinate to the fabrication gate)."""
import unittest
from fides import assess_slop, slop_score, flag_slop_sentences, Gate, NumericCheck, GroundedGenerator
from fides.numeric import ledger

SLOPPY = ("In today's fast-paced world, it's important to note that AI plays a crucial role. "
          "Let's dive into this rich tapestry. Needless to say, the possibilities are endless.")
CONCRETE = "Apex Growth returned 12.4% net in FY2024, beating its benchmark's 9.8% by 2.6 points."


class SlopDetection(unittest.TestCase):
    def test_sloppy_scores_higher_than_concrete(self):
        self.assertGreater(slop_score(SLOPPY), slop_score(CONCRETE))
        self.assertGreater(slop_score(SLOPPY), 0.5)
        self.assertLess(slop_score(CONCRETE), 0.3)

    def test_flags_name_the_cliches(self):
        flags = flag_slop_sentences(SLOPPY)
        joined = " ".join(f["sentence"] + " ".join(f["reasons"]) for f in flags)
        self.assertIn("today's", joined)
        self.assertTrue(any("cliché" in r for f in flags for r in f["reasons"]))

    def test_concrete_text_flags_little(self):
        self.assertEqual(flag_slop_sentences(CONCRETE), [])

    def test_assess_slop_report(self):
        r = assess_slop(SLOPPY)
        self.assertTrue(r["is_slop"])
        self.assertGreater(len(r["flags"]), 0)
        self.assertFalse(assess_slop(CONCRETE)["is_slop"])

    def test_empty_text_is_safe(self):
        self.assertEqual(slop_score(""), 0.0)


class SlopIsSeparateFromFaithfulness(unittest.TestCase):
    def test_gate_reports_slop_but_never_drops_on_it(self):
        # a sloppy but TRUE claim publishes (slop is advisory) and the report carries the slop score
        facts = {f["id"]: f for f in [ledger.materialize_fact({"id": "f1", "value": "12.4%", "subject": "Apex", "metric": "net return", "locatorText": "..."})]}
        gate = Gate(checks=[NumericCheck()])
        span = {"id": "s1", "surface": "compliance",
                "text": "In today's fast-paced world, Apex returned 12.4%, a true testament to its strategy.",
                "facts_by_id": facts,
                "numeric_claims": [{"emitted": "12.4%", "binding": {"kind": "source", "factId": "f1"}, "context": {"surface": "compliance", "subject": "Apex", "metric": "net return"}}]}
        r = gate.run([span])
        self.assertTrue(r.decisions[0].published)      # faithfulness passed; slop does NOT drop it
        self.assertIn("score", r.slop)                 # but the slop score is surfaced (advisory)
        self.assertGreater(r.slop["score"], 0)


class DeslopSubordinateToFaithfulness(unittest.TestCase):
    FACTS = {f["id"]: f for f in [ledger.materialize_fact({"id": "f1", "value": "12.4%", "subject": "Apex", "metric": "net return", "locatorText": "Apex returned 12.4% net."})]}

    def _span(self, text, emitted="12.4%", binding=None):
        binding = binding or {"kind": "source", "factId": "f1"}
        return {"id": "s1", "surface": "compliance", "text": text, "facts_by_id": self.FACTS,
                "numeric_claims": [{"emitted": emitted, "binding": binding, "context": {"surface": "compliance", "subject": "Apex", "metric": "net return"}}]}

    # a realistic mixed draft: a filler sentence + a fact sentence
    SLOPPY_DRAFT = "In today's fast-paced world, needless to say, the possibilities are endless. Apex returned 12.4% net."

    def test_deslop_rewrites_a_faithful_sloppy_span(self):
        gate = Gate(checks=[NumericCheck()])
        drafter = lambda intent: self._span(self.SLOPPY_DRAFT)
        slop_repairer = lambda intent, span, report: self._span("Apex returned 12.4% net.")  # trims filler, keeps the number
        gen = GroundedGenerator(gate, drafter, slop_repairer=slop_repairer, slop_threshold=0.35)
        r = gen.generate([{"id": "c1"}])
        self.assertIn("12.4%", r.text)
        self.assertNotIn("fast-paced", r.text)  # slop removed

    def test_deslop_that_breaks_faithfulness_is_rejected(self):
        gate = Gate(checks=[NumericCheck()])
        drafter = lambda intent: self._span(self.SLOPPY_DRAFT)
        # a 'de-slop' that secretly changes the number to an unverifiable one must be REJECTED
        bad = lambda intent, span, report: self._span("Apex returned 40%.", emitted="40%", binding={"kind": "unbound"})
        gen = GroundedGenerator(gate, drafter, slop_repairer=bad, slop_threshold=0.35)
        r = gen.generate([{"id": "c1"}])
        self.assertIn("12.4%", r.text)          # kept the original faithful (if sloppy) text
        self.assertNotIn("40%", r.text)          # the truth-breaking rewrite was rejected


if __name__ == "__main__":
    unittest.main()
