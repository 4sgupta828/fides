"""Anti-slop tripwires — deterministic quality signals, and the Goodhart pattern detector."""
import unittest
from faithful_core import quality_signals, goodhart_tripwire


class Quality(unittest.TestCase):
    def test_signals_count_value_tokens_and_hedges(self):
        s = quality_signals("Revenue grew to $1.2B, up 26%. It might improve further, some say.")
        self.assertGreaterEqual(s["value_token_count"], 2)   # $1.2B, 26%
        self.assertGreater(s["value_density_per_100w"], 0)
        self.assertGreater(s["hedge_sentence_rate"], 0)      # "might", "some say"

    def test_concrete_text_has_low_hedge_high_density(self):
        concrete = quality_signals("Net return was 12.4% in FY2024. AUM reached $1.2B.")
        vague = quality_signals("Performance may have been reasonable. Results possibly improved, some say.")
        self.assertGreater(concrete["value_density_per_100w"], vague["value_density_per_100w"])
        self.assertLess(concrete["hedge_sentence_rate"], vague["hedge_sentence_rate"])

    def test_goodhart_tripwire_fires_on_evasion(self):
        before = quality_signals("Net return was 12.4% in FY2024, beating the 9.8% benchmark by 2.6 points.")
        after = quality_signals("Performance was arguably strong and may have exceeded expectations, some say.")
        trip = goodhart_tripwire(before, after, escape_improved=True)
        self.assertTrue(trip["triggered"])  # escape down BUT vaguer + more hedged

    def test_goodhart_quiet_when_content_stays_concrete(self):
        before = quality_signals("Return was 12.4%.")
        after = quality_signals("Net return was 12.4% in FY2024, net of a 65 bps fee.")
        trip = goodhart_tripwire(before, after, escape_improved=True)
        self.assertFalse(trip["triggered"])  # concreteness rose, not fell

    def test_empty_text_is_safe(self):
        s = quality_signals("")
        self.assertEqual(s["word_count"], 0)
        self.assertEqual(s["value_density_per_100w"], 0.0)


if __name__ == "__main__":
    unittest.main()
