"""Grounded generation: the verifier-as-critic repair loop. Deterministic drafter/repairer prove the
plan→draft→verify→repair mechanism without any LLM."""
import unittest
from faithful_core import Gate, NumericCheck, GroundedGenerator
from faithful_core.numeric import ledger


FACTS = {f["id"]: f for f in [
    ledger.materialize_fact({"id": "f1", "value": "12.4%", "subject": "Apex", "metric": "net return",
                             "locatorText": "Apex returned 12.4% net."}),
]}


def span(id, text, emitted, binding):
    return {"id": id, "surface": "compliance", "text": text, "facts_by_id": FACTS,
            "numeric_claims": [{"emitted": emitted, "binding": binding,
                                "context": {"surface": "compliance", "subject": "Apex", "metric": "net return"}}]}


class Generate(unittest.TestCase):
    def setUp(self):
        self.gate = Gate(checks=[NumericCheck()])

    def test_clean_claim_accepted_no_repair(self):
        drafter = lambda intent: span(intent["id"], "Apex returned 12.4%", "12.4%", {"kind": "source", "factId": "f1"})
        gen = GroundedGenerator(self.gate, drafter)
        r = gen.generate([{"id": "c1"}])
        self.assertEqual(len(r.accepted), 1)
        self.assertEqual(r.repair_count, 0)

    def test_verifier_drives_a_successful_repair(self):
        # first draft fabricates a number; the repairer fixes it to the grounded value → then it passes
        def drafter(intent):
            return span(intent["id"], "Apex returned 15%", "15%", {"kind": "source", "factId": "f1"})  # 15% != 12.4% → value_mismatch

        def repairer(intent, sp, decision):
            # uses the finding reason to fix the number to the source cell
            return span(intent["id"], "Apex returned 12.4%", "12.4%", {"kind": "source", "factId": "f1"})

        gen = GroundedGenerator(self.gate, drafter, repairer, max_repairs=2)
        r = gen.generate([{"id": "c1"}])
        self.assertEqual(len(r.accepted), 1)
        self.assertEqual(r.repair_count, 1)
        self.assertIn("12.4%", r.text)
        self.assertEqual(r.trace[0].outcome, "accepted")

    def test_unrepairable_claim_is_dropped_after_budget(self):
        # the repairer can't fix it (returns the same fabricated span) → dropped after max_repairs
        def drafter(intent):
            return span(intent["id"], "Apex returned 40%", "40%", {"kind": "unbound"})
        repairer = lambda intent, sp, d: sp
        gen = GroundedGenerator(self.gate, drafter, repairer, max_repairs=2)
        r = gen.generate([{"id": "c1"}])
        self.assertEqual(len(r.dropped), 1)
        self.assertEqual(r.trace[0].outcome, "dropped")
        self.assertEqual(r.trace[0].repairs, 2)  # tried the full budget
        self.assertEqual(r.text, "")  # nothing ungrounded shipped

    def test_mixed_plan_composes_only_grounded_text(self):
        def drafter(intent):
            if intent["id"] == "good":
                return span("good", "Apex returned 12.4%", "12.4%", {"kind": "source", "factId": "f1"})
            return span("bad", "Apex returned 99%", "99%", {"kind": "unbound"})
        gen = GroundedGenerator(self.gate, drafter, repairer=None)  # no repair → bad is dropped
        r = gen.generate([{"id": "good"}, {"id": "bad"}])
        self.assertIn("12.4%", r.text)
        self.assertNotIn("99%", r.text)  # the fabricated claim never reaches the output


if __name__ == "__main__":
    unittest.main()
