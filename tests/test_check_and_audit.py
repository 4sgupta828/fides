"""End-to-end: NumericCheck emits Findings → policy composes a publish decision; audit exports the
source documentation for what shipped and what was withheld."""
import unittest
from faithful_core import NumericCheck, compose_decision, is_published, build_audit_report, render_audit_markdown, DEFAULT_MANIFEST
from faithful_core.numeric import ledger


class CheckAndAudit(unittest.TestCase):
    def setUp(self):
        self.facts = {f["id"]: f for f in [
            ledger.materialize_fact({"id": "f1", "value": "12.4%", "subject": "Apex Fund", "metric": "net return",
                                     "period": "FY2024", "locatorText": "Apex returned 12.4% net in FY2024."}),
        ]}
        self.genuine = {"emitted": "12.4%", "binding": {"kind": "source", "factId": "f1"},
                        "context": {"surface": "compliance", "subject": "Apex Fund", "metric": "net return"}}
        self.fabricated = {"emitted": "18%", "binding": {"kind": "unbound"}, "context": {"surface": "compliance"}}

    def test_check_emits_findings_and_policy_decides(self):
        findings = NumericCheck().run([self.genuine, self.fabricated],
                                      {"facts_by_id": self.facts, "surface": "compliance"}, DEFAULT_MANIFEST)
        self.assertEqual(len(findings), 2)
        # genuine → in_corpus → keep → published; fabricated → unbound(false) → drop → withheld
        a_genuine, _ = compose_decision([findings[0]])
        a_fab, _ = compose_decision([findings[1]])
        self.assertTrue(is_published(a_genuine))
        self.assertFalse(is_published(a_fab))

    def test_check_is_fail_safe_on_bad_input(self):
        # a malformed claim must ABSTAIN, never raise into the gate
        findings = NumericCheck().run([{"emitted": "5%", "binding": {"kind": "source"}, "context": {}}],
                                      {"facts_by_id": self.facts, "surface": "compliance"})
        self.assertEqual(findings[0].groundedness, "abstain")

    def test_audit_report_and_markdown(self):
        report = build_audit_report([self.genuine, self.fabricated], self.facts)
        self.assertEqual(report["summary"]["verified"], 1)
        self.assertEqual(report["summary"]["withheld"], 1)
        md = render_audit_markdown(report, title="Apex Q4", stamped_at="2026-08-18")
        self.assertIn("1/2 figures verified", md)
        self.assertIn("Apex returned 12.4% net in FY2024.", md)  # verbatim source locator in the doc
        self.assertIn("✗ withheld (unbound)", md)


if __name__ == "__main__":
    unittest.main()
