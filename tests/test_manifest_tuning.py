"""The platform bet in one test: the SAME calculus, tuned by a domain unit vocab, parses domain
numbers differently — proving 'vocabulary is data, mechanism is kernel'."""
import unittest
from faithful_core.numeric import ledger
from faithful_core.manifest import DEFAULT_VOCAB, INDIA_TECH_VOCAB, UnitVocab


class ManifestTuning(unittest.TestCase):
    def test_crore_needs_the_india_vocab(self):
        # default vocab doesn't know "crore" → magnitude 1
        default_q = ledger.parse_quantity("₹5 crore", DEFAULT_VOCAB)
        self.assertEqual(default_q["unit"], {"kind": "currency", "code": "INR"})
        self.assertEqual(default_q["canonical"], 5)  # crore unknown → not scaled
        # the tuned vocab scales it to 5 crore = 5e7
        india_q = ledger.parse_quantity("₹5 crore", INDIA_TECH_VOCAB)
        self.assertEqual(india_q["canonical"], 5e7)

    def test_custom_currency_vocab(self):
        vocab = UnitVocab(magnitudes=dict(DEFAULT_VOCAB.magnitudes),
                          currencies=dict(DEFAULT_VOCAB.currencies, **{"₩": "KRW"}))
        q = ledger.parse_quantity("₩500", vocab)
        self.assertEqual(q["unit"], {"kind": "currency", "code": "KRW"})

    def test_default_calculus_unchanged_by_tuning(self):
        # tuning adds vocabulary; it never changes the fixed calculus for known units
        self.assertEqual(ledger.parse_quantity("$1.2B", INDIA_TECH_VOCAB)["canonical"], 1.2e9)


if __name__ == "__main__":
    unittest.main()
