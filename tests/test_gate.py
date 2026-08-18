"""The Gate — one call, one verdict across all checks. Mixes deterministic numeric + llm_judge
semantic checks over each span and composes a single publish decision."""
import unittest
from fides import Gate, NumericCheck, EntailmentCheck, format_gate_report
from fides.numeric import ledger


def scripted(mapping):
    def _j(text, ev):
        return mapping.get(text, {"verdict": "abstain", "confidence": 0.0, "reason": ""})
    return _j


class GateTest(unittest.TestCase):
    def setUp(self):
        facts = {f["id"]: f for f in [
            ledger.materialize_fact({"id": "f1", "value": "12.4%", "subject": "Apex", "metric": "net return",
                                     "locatorText": "Apex returned 12.4% net."}),
        ]}
        self.facts = facts
        self.gate = Gate(checks=[
            NumericCheck(),
            EntailmentCheck(judge=scripted({
                "Apex beat its benchmark": {"verdict": "supported", "confidence": 0.9, "reason": ""},
                "Apex is the best fund ever": {"verdict": "violated", "confidence": 0.9, "reason": "unsupported superlative"},
            })),
        ])

    def span(self, id, text, emitted, binding, ctx):
        return {"id": id, "surface": "compliance", "text": text,
                "facts_by_id": self.facts,
                "numeric_claims": [{"emitted": emitted, "binding": binding, "context": dict({"surface": "compliance"}, **ctx)}],
                "evidence_texts": ["Apex returned 12.4% net."]}

    def test_clean_span_publishes(self):
        r = self.gate.run([self.span("s1", "Apex beat its benchmark", "12.4%",
                                     {"kind": "source", "factId": "f1"}, {"subject": "Apex", "metric": "net return"})])
        self.assertTrue(r.decisions[0].published)
        self.assertEqual(r.summary["published"], 1)

    def test_fabricated_number_drops_the_span(self):
        # a deterministic false → drop (the immovable invariant), regardless of the entailment verdict
        r = self.gate.run([self.span("s2", "Apex beat its benchmark", "40%",
                                     {"kind": "unbound"}, {})])
        self.assertFalse(r.decisions[0].published)
        self.assertEqual(r.decisions[0].action, "drop")
        self.assertEqual(r.decisions[0].driver_dimension, "numeric")

    def test_judge_violation_holds_the_span_on_compliance(self):
        # numeric is fine, but the entailment judge says violated → llm_judge holds (never drops)
        r = self.gate.run([self.span("s3", "Apex is the best fund ever", "12.4%",
                                     {"kind": "source", "factId": "f1"}, {"subject": "Apex", "metric": "net return"})])
        self.assertFalse(r.decisions[0].published)
        self.assertEqual(r.decisions[0].action, "hold")
        self.assertEqual(r.decisions[0].driver_dimension, "entailment")

    def test_report_has_quality_signal_and_formats(self):
        r = self.gate.run([self.span("s1", "Apex beat its benchmark", "12.4%",
                                     {"kind": "source", "factId": "f1"}, {"subject": "Apex", "metric": "net return"})])
        self.assertIn("value_density_per_100w", r.quality)  # quality tripwire over published text
        self.assertIn("Gate verdict", format_gate_report(r))


if __name__ == "__main__":
    unittest.main()
