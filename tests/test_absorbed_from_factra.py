"""Tests for the battle-tested behaviors absorbed from factra: the fuzzy span gate, the prose
value-leak audit, and the Gate's fail-closed coverage guard."""
import unittest
from faithful_core import (
    QuoteCheck, verify_span, verify_span_any, value_present_in_prose, leaked_values,
    Gate, NumericCheck, surface_policy, GateManifest,
)
from faithful_core.numeric import ledger


class SpanGate(unittest.TestCase):
    PASSAGE = "Apex Growth returned 12.4% net of fees in FY2024, beating the benchmark."

    def test_exact_after_normalization(self):
        # smart quotes / dashes / whitespace drift still verify
        self.assertTrue(verify_span(self.PASSAGE, "returned 12.4% net of fees")["verified"])

    def test_smart_quote_and_whitespace_drift(self):
        passage = "The board said “no rate increase” this\n\n year."
        self.assertTrue(verify_span(passage, 'said "no rate increase" this year')["verified"])

    def test_fuzzy_tolerates_small_edits(self):
        self.assertTrue(verify_span(self.PASSAGE, "returned 12.4% net of fee in FY2024")["verified"])

    def test_fabricated_quote_is_absent(self):
        self.assertFalse(verify_span(self.PASSAGE, "guaranteed a 30% return to investors")["verified"])

    def test_too_short_fails_closed(self):
        self.assertEqual(verify_span(self.PASSAGE, "net")["method"], "too_short")

    def test_quote_check_grounds_and_drops(self):
        chk = QuoteCheck()
        f_ok = chk.run([{"text": "returned 12.4% net of fees", "evidence_texts": [self.PASSAGE]}], {"surface": "compliance"})[0]
        self.assertEqual(f_ok.groundedness, "in_corpus")
        f_bad = chk.run([{"text": "guaranteed a 30% return to investors", "evidence_texts": [self.PASSAGE]}], {"surface": "compliance"})[0]
        self.assertEqual(f_bad.groundedness, "false")
        self.assertEqual(surface_policy(f_bad), "drop")  # proven fabrication → invariant drop


class ProseLeak(unittest.TestCase):
    def test_value_shaped_leak_detected(self):
        self.assertTrue(value_present_in_prose("The fund posted 12.4% net.", "12.4%"))
        self.assertTrue(value_present_in_prose("AUM was $190.28 million.", "$190.28"))

    def test_bare_year_or_count_is_not_policed(self):
        self.assertFalse(value_present_in_prose("This was true in 2018.", "2018"))
        self.assertFalse(value_present_in_prose("There were 5000 filings.", "5000"))

    def test_no_substring_false_match(self):
        self.assertFalse(value_present_in_prose("Revenue was $1190.28.", "190.28"))  # not standalone

    def test_leaked_values_list(self):
        self.assertEqual(leaked_values("We returned 12.4% net.", ["12.4%", "18%"]), ["12.4%"])


class FailClosedCoverage(unittest.TestCase):
    def test_uncheckable_span_holds_on_compliance_not_publishes(self):
        gate = Gate(checks=[NumericCheck()])
        # a span with text but no numeric_claims and no numeric check output → coverage abstain
        r = gate.run([{"id": "s1", "surface": "compliance", "text": "Something unverifiable was asserted."}])
        self.assertFalse(r.decisions[0].published)   # fail-CLOSED (was fail-open before)
        self.assertEqual(r.decisions[0].action, "hold")

    def test_gate_reports_leaked_values(self):
        facts = {f["id"]: f for f in [ledger.materialize_fact({"id": "f1", "value": "12.4%", "subject": "Apex", "metric": "net return", "locatorText": "..."})]}
        gate = Gate(checks=[NumericCheck()])
        spans = [
            {"id": "keep", "surface": "compliance", "text": "The fund returned 12.4%.",
             "facts_by_id": facts, "numeric_claims": [{"emitted": "12.4%", "binding": {"kind": "source", "factId": "f1"}, "context": {"surface": "compliance", "subject": "Apex", "metric": "net return"}}]},
            # a withheld span whose number (12.4%) leaks into the kept span's prose above
            {"id": "bad", "surface": "compliance", "text": "x", "facts_by_id": facts,
             "numeric_claims": [{"emitted": "12.4%", "binding": {"kind": "unbound"}, "context": {"surface": "compliance"}}]},
        ]
        r = gate.run(spans)
        self.assertIn("12.4%", r.summary["leaked_values"])  # withheld number survived in published prose


if __name__ == "__main__":
    unittest.main()
