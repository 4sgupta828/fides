"""Policy table + the immovable fabrication invariant + composition."""
import unittest
from faithful_core.finding import (
    Finding, ContentSpan, surface_policy, compose_decision, is_published, default_policy,
)


def F(groundedness, kind, surface):
    return Finding(check_id="c", dimension="numeric", kind=kind,
                   span=ContentSpan(text="x", surface=surface), groundedness=groundedness, severity="high")


class Policy(unittest.TestCase):
    def test_deterministic_false_always_drops(self):
        # the immovable invariant — no tier, no policy override
        self.assertEqual(surface_policy(F("false", "deterministic", "compliance")), "drop")
        self.assertEqual(surface_policy(F("false", "deterministic", "marketing")), "drop")

    def test_judge_false_holds_on_compliance_flags_on_marketing(self):
        self.assertEqual(surface_policy(F("false", "llm_judge", "compliance")), "hold")
        self.assertEqual(surface_policy(F("false", "llm_judge", "marketing")), "flag")

    def test_general_knowledge_tiering(self):
        self.assertEqual(surface_policy(F("true_uncited", "deterministic", "compliance")), "drop")
        self.assertEqual(surface_policy(F("true_uncited", "llm_judge", "marketing")), "keep")

    def test_creative_dial_cannot_override_fabrication(self):
        # a maximally-permissive custom table keeps general knowledge on compliance...
        creative = default_policy()
        creative[("compliance", "true_uncited", "deterministic")] = "keep"
        self.assertEqual(surface_policy(F("true_uncited", "deterministic", "compliance"), creative), "keep")
        # ...but the invariant still drops a proven fabrication regardless of the table.
        self.assertEqual(surface_policy(F("false", "deterministic", "compliance"), creative), "drop")

    def test_compose_most_restrictive_wins(self):
        keep = F("in_corpus", "deterministic", "compliance")
        drop = F("false", "deterministic", "compliance")
        action, driver = compose_decision([keep, drop])
        self.assertEqual(action, "drop")
        self.assertEqual(driver.groundedness, "false")

    def test_is_published(self):
        self.assertTrue(is_published("flag"))
        self.assertFalse(is_published("hold"))
        self.assertFalse(is_published("drop"))


if __name__ == "__main__":
    unittest.main()
