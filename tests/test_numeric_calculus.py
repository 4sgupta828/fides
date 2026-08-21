"""Adversarial calculus tests — the cases the n-gram gate gets wrong (mirrors the TS suite)."""
import unittest
from fides.numeric import ledger


def fact(fid, value, subject, metric, **kw):
    return ledger.materialize_fact(dict({"id": fid, "value": value, "subject": subject, "metric": metric}, **kw))


def claim(emitted, binding, **ctx):
    return {"emitted": emitted, "binding": binding, "context": dict({"surface": "compliance"}, **ctx)}


def src(fid):
    return {"kind": "source", "factId": fid}


class Calculus(unittest.TestCase):
    def verdict(self, claim_, facts, opts=None):
        return ledger.verify_claim(claim_, {f["id"]: f for f in facts}, opts or {})

    def test_bps_no_collapse(self):
        self.assertFalse(ledger.values_equal(ledger.parse_quantity("40 bps"), ledger.parse_quantity("10 bps")["canonical"]))
        self.assertTrue(ledger.values_equal(ledger.parse_quantity("40 bps"), ledger.parse_quantity("40.2 bps")["canonical"]))

    def test_magnitude_rounding(self):
        self.assertTrue(ledger.values_equal(ledger.parse_quantity("$1.2B"), ledger.parse_quantity("$1.23B")["canonical"]))
        self.assertFalse(ledger.values_equal(ledger.parse_quantity("$1.2B"), ledger.parse_quantity("$1.26B")["canonical"]))

    def test_wrong_but_real_cell(self):
        f_ret = fact("f1", "72%", "Fund A", "net return")
        f_exp = fact("f2", "72%", "Fund A", "expense ratio")
        v = self.verdict(claim("72%", src("f2"), subject="Fund A", metric="net return"), [f_ret, f_exp])
        self.assertEqual(v["code"], "entity_mismatch")

    def test_unit_swap(self):
        f = fact("f1", "72%", "Fund A", "net return")
        self.assertEqual(self.verdict(claim("$72M", src("f1"), subject="Fund A", metric="net return"), [f])["code"], "unit_mismatch")

    def test_derived_growth_ok_and_incoherent(self):
        a = fact("f1", "5,000", "ARR", "customers"); b = fact("f2", "7,000", "ARR", "customers")
        ok = self.verdict(claim("40%", {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["f1", "f2"]}}, subject="ARR"), [a, b])
        self.assertTrue(ok["ok"])
        bad_b = fact("f2", "7,000", "Fund B", "customers")
        inc = self.verdict(claim("40%", {"kind": "derived", "derivation": {"op": "growth_pct", "operandFactIds": ["f1", "f2"]}}), [a, bad_b])
        self.assertEqual(inc["code"], "operands_incoherent")

    def test_period_half_vs_fy(self):
        f = fact("f1", "8%", "Fund A", "return", period="FY2024")
        v = self.verdict(claim("8%", src("f1"), subject="Fund A", metric="return", period="H1 2024"), [f])
        self.assertEqual(v["code"], "period_mismatch")

    def test_strict_entity_unresolved(self):
        f = fact("f1", "72%", "Fund A", "net return")
        lenient = self.verdict(claim("72%", src("f1")), [f])
        self.assertTrue(lenient["ok"])
        strict = self.verdict(claim("72%", src("f1")), [f], {"strict": True})
        self.assertEqual(strict["code"], "entity_unresolved")

    def test_period_strictness_is_opt_in(self):
        f = fact("f1", "8%", "Fund A", "return", period="FY2024")
        c = claim("8%", src("f1"), subject="Fund A", metric="return")  # context omits the period
        self.assertTrue(self.verdict(c, [f], {"strict": True})["ok"])  # entity-strict alone ships it
        self.assertEqual(self.verdict(c, [f], {"strict": True, "strict_period": True})["code"], "period_unresolved")

    def test_subjects_match_not_containment(self):
        self.assertFalse(ledger.subjects_match("net return", "return"))
        self.assertTrue(ledger.subjects_match("return net", "net return"))

    def test_named_unit_token_not_collapsed_to_count(self):
        # regression: mg and mcg once both parsed as bare 'count' → 100 mg == 100 mcg (1000x dose escape)
        self.assertFalse(ledger.units_congruent(ledger.parse_quantity("100 mg")["unit"], ledger.parse_quantity("100 mcg")["unit"]))
        f = fact("d", "100 mg", "DrugX", "dose")
        self.assertEqual(self.verdict(claim("100 mcg", src("d"), subject="DrugX", metric="dose"), [f])["code"], "unit_mismatch")
        self.assertTrue(self.verdict(claim("100 mg", src("d"), subject="DrugX", metric="dose"), [f])["ok"])

    def test_labeled_unit_self_congruent_and_bare_decimal_ships(self):
        # a labeled unit verifies against itself (grounded-by-construction), unlike the old bare 'unknown'
        self.assertTrue(ledger.units_congruent(ledger.parse_quantity("18.6 GW")["unit"], ledger.parse_quantity("9.1 GW")["unit"]))
        for raw in ("18.6 GW", "1.94", "89"):
            f = fact("x", raw, "grid", "cap")
            self.assertTrue(self.verdict(claim(raw, src("x"), subject="grid", metric="cap"), [f])["ok"], raw)


if __name__ == "__main__":
    unittest.main()
