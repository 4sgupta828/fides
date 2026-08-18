"""Property / fuzz-style invariants for the numeric ledger — deterministic (no RNG), broad coverage.
These catch classes of regressions a fixed golden set won't."""
import unittest
from fides.numeric import ledger

SAMPLES = [
    "72%", "0%", "100%", "72.4%", "40 bps", "5 bps", "$5", "$5.00", "$1.2B", "$1,200M",
    "€5M", "£3.5bn", "₹5 crore", "3x", "3:1", "18 months", "7,000", "0", "-12%", "1.5x",
    "$0.65", "9.8%", "2.6%", "$350K", "$4.2M", "13.1%",
]


class NumericProperties(unittest.TestCase):
    def test_every_sample_parses_to_finite_canonical(self):
        for s in SAMPLES:
            q = ledger.parse_quantity(s)
            self.assertIsNotNone(q, s)
            self.assertTrue(isinstance(q["canonical"], float) or isinstance(q["canonical"], int), s)
            self.assertEqual(q["canonical"], q["canonical"], s)  # not NaN

    def test_reflexive_equality(self):
        # a parsed quantity always equals its own canonical value
        for s in SAMPLES:
            q = ledger.parse_quantity(s)
            self.assertTrue(ledger.values_equal(q, q["canonical"]), s)

    def test_units_congruent_symmetric_and_reflexive(self):
        units = [ledger.parse_quantity(s)["unit"] for s in SAMPLES]
        for a in units:
            self.assertTrue(ledger.units_congruent(a, a) or a["kind"] == "unknown")
            for b in units:
                self.assertEqual(ledger.units_congruent(a, b), ledger.units_congruent(b, a))

    def test_non_numeric_returns_none(self):
        for s in ["several", "many", "a lot", "", "TBD", "n/a"]:
            self.assertIsNone(ledger.parse_quantity(s), s)

    def test_rounding_is_monotone_tightening(self):
        # a coarser emitted value tolerates more slack than a finer one
        source = ledger.parse_quantity("72.4%")["canonical"]
        self.assertTrue(ledger.values_equal(ledger.parse_quantity("72%"), source))     # 0 decimals: 72.4 rounds to 72
        self.assertFalse(ledger.values_equal(ledger.parse_quantity("72.0%"), source))  # 1 decimal: 72.4 != 72.0

    def test_recompute_never_raises_on_valid_ops(self):
        for op in ("identity", "sum", "difference", "delta", "growth_pct", "share_of", "ratio", "product", "quotient", "annualize"):
            arity = 1 if op in ("identity", "annualize") else 2
            r = ledger.recompute(op, [10.0, 4.0][:arity])
            self.assertTrue(r is None or isinstance(r, float))

    def test_derivation_arity_guarded(self):
        self.assertIsNone(ledger.recompute("difference", [1.0]))       # too few
        self.assertIsNone(ledger.recompute("growth_pct", [1.0, 2.0, 3.0]))  # too many
        self.assertIsNone(ledger.recompute("quotient", [1.0, 0.0]))    # div by zero → None, not raise


if __name__ == "__main__":
    unittest.main()
