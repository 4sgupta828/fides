"""Tests for the second absorb batch: robust judges (tri-state/chunking/caching), verbatim raw-match,
cross-origin guard, retry, authority floor."""
import unittest
from fides import (
    JudgeCache, make_cached_judge, with_retry, make_chunked_batch_judge,
    OriginScopedEvidence, all_proposal_grade, NumericCheck, GateManifest,
)
from fides.numeric import ledger


# ---- #4 robust judges ----------------------------------------------------------------------------
class RobustJudge(unittest.TestCase):
    def test_caching_skips_the_second_call(self):
        calls = {"n": 0}
        def judge(c, e):
            calls["n"] += 1
            return {"verdict": "supported", "confidence": 0.9}
        cache = JudgeCache()
        j = make_cached_judge(judge, cache, model_tag="gpt-4o-mini", prompt_version="v1")
        r1 = j("claim", ["ev"]); r2 = j("claim", ["ev"])
        self.assertEqual(calls["n"], 1)          # second call served from cache
        self.assertTrue(r2.get("cached"))
        self.assertEqual(len(cache), 1)

    def test_model_or_prompt_change_busts_the_cache(self):
        calls = {"n": 0}
        judge = lambda c, e: (calls.__setitem__("n", calls["n"] + 1) or {"verdict": "supported"})
        cache = JudgeCache()
        make_cached_judge(judge, cache, "gpt-4o-mini", "v1")("c", ["e"])
        make_cached_judge(judge, cache, "gpt-4o-mini", "v2")("c", ["e"])  # new prompt version
        self.assertEqual(calls["n"], 2)

    def test_error_is_not_judged_not_false_and_not_cached(self):
        state = {"fail": True}
        def judge(c, e):
            if state["fail"]:
                raise RuntimeError("api down")
            return {"verdict": "supported"}
        cache = JudgeCache()
        j = make_cached_judge(judge, cache)
        r = j("c", ["e"])
        self.assertTrue(r["not_judged"])         # tri-state: errored != judged-false
        self.assertEqual(r["verdict"], "abstain")
        self.assertEqual(len(cache), 0)          # errors are not cached → retried
        state["fail"] = False
        self.assertEqual(j("c", ["e"])["verdict"], "supported")

    def test_retry_then_succeed(self):
        state = {"n": 0}
        def flaky(c, e):
            state["n"] += 1
            if state["n"] < 3:
                raise RuntimeError("transient")
            return {"verdict": "supported"}
        j = with_retry(flaky, retries=2, backoff=0.0)
        self.assertEqual(j("c", ["e"])["verdict"], "supported")
        self.assertEqual(state["n"], 3)

    def test_chunking_caps_blast_radius(self):
        # a batch judge that raises only for the chunk containing "boom"
        def batch(items):
            if any(c == "boom" for c, _ in items):
                raise ValueError("derailed")
            return [{"verdict": "supported"} for _ in items]
        run = make_chunked_batch_judge(batch, chunk_size=2)
        items = [("ok1", []), ("ok2", []), ("boom", []), ("ok4", [])]  # boom lands in chunk 2
        out = run(items)
        self.assertEqual(out[0]["verdict"], "supported")  # chunk 1 unaffected
        self.assertEqual(out[1]["verdict"], "supported")
        self.assertTrue(out[2]["not_judged"])             # only chunk 2 fails
        self.assertTrue(out[3]["not_judged"])


# ---- #1 verbatim / wrong-cell ------------------------------------------------------------------
class Verbatim(unittest.TestCase):
    def _v(self, emitted, source_text, verbatim):
        fact = ledger.materialize_fact({"id": "f1", "value": source_text.strip(), "subject": "Rate", "metric": "cost",
                                        "locatorText": "The rate is %s per unit." % source_text.strip()})
        claim = {"emitted": emitted, "binding": {"kind": "source", "factId": "f1"},
                 "context": {"surface": "cell", "subject": "Rate", "metric": "cost"}}
        return ledger.verify_claim(claim, {"f1": fact}, {"verbatim": verbatim})

    def test_display_drift_passes_tolerant_but_fails_verbatim(self):
        # $1.79 vs a source cell of $1.790 — canonically equal (tolerant OK) but NOT the exact cell
        self.assertTrue(self._v("$1.79", "$1.790", verbatim=False)["ok"])
        self.assertEqual(self._v("$1.79", "$1.790", verbatim=True)["code"], "raw_mismatch")

    def test_exact_cell_passes_verbatim(self):
        self.assertTrue(self._v("$1.790", "$1.790", verbatim=True)["ok"])


# ---- #7 cross-origin guard ---------------------------------------------------------------------
class CrossOrigin(unittest.TestCase):
    def test_same_id_different_origin_never_collides(self):
        ev = OriginScopedEvidence()
        ev.add("corpus", "42", {"value": "corpus fact"})
        ev.add("tenantB", "42", {"value": "tenant B fact"})
        self.assertEqual(ev.get("corpus", "42")["value"], "corpus fact")
        self.assertEqual(ev.get("tenantB", "42")["value"], "tenant B fact")

    def test_unknown_origin_returns_none_never_falls_back(self):
        ev = OriginScopedEvidence()
        ev.add("corpus", "42", {"value": "x"})
        self.assertIsNone(ev.get("other_tenant", "42"))  # no cross-origin fallback (false-pass guard)


# ---- #2 authority floor ------------------------------------------------------------------------
class Authority(unittest.TestCase):
    PROPOSAL = frozenset({"application", "testimony", "press_release", "pending"})

    def test_all_proposal_grade(self):
        self.assertTrue(all_proposal_grade(["application", "testimony"], self.PROPOSAL))
        self.assertFalse(all_proposal_grade(["application", "order"], self.PROPOSAL))  # one realized-grade
        self.assertFalse(all_proposal_grade([], self.PROPOSAL))                        # nothing cited → don't floor


if __name__ == "__main__":
    unittest.main()
