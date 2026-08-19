"""Production hardening for LLM judges — absorbed from factra (claims_first/claim_gate.py). Three
independent wins that wrap ANY injected judge (offline-testable with fakes):

  CACHING  — a verdict is a pure function of (claim, evidence, model, prompt); cache it, never pay
             to re-judge an immutable input. The key MUST fold in model+prompt version (Rule 11).
  TRI-STATE— an errored judge is 'not_judged' (distinct from a genuine 'abstain' verdict), and is
             NOT cached, so a transient failure is retried — never a fabricated negative.
  CHUNKING — batch judging with a blast-radius cap: one oversized/derailed call can't sink every
             claim it carried; a failing chunk yields not_judged for ITS claims only.
"""
from __future__ import annotations
import hashlib
import time
from typing import Callable, List, Tuple


def _key(claim: str, evidence: List[str], tag: str) -> str:
    h = hashlib.sha256()
    h.update(claim.encode("utf-8")); h.update(b"\x00")
    for e in evidence:
        h.update(e.encode("utf-8")); h.update(b"\x00")
    h.update(tag.encode("utf-8"))
    return h.hexdigest()


class JudgeCache:
    def __init__(self):
        self._d = {}
    def get(self, k):
        return self._d.get(k)
    def put(self, k, v):
        self._d[k] = v
    def __len__(self):
        return len(self._d)


def make_cached_judge(judge: Callable, cache: JudgeCache, model_tag: str = "", prompt_version: str = "v1"):
    """Wrap a per-claim judge with caching + tri-state error handling."""
    tag = "%s/%s" % (model_tag, prompt_version)

    def wrapped(claim_text: str, evidence_texts: List[str]) -> dict:
        k = _key(claim_text, list(evidence_texts), tag)
        hit = cache.get(k)
        if hit is not None:
            return dict(hit, cached=True)
        try:
            r = judge(claim_text, evidence_texts)
        except Exception as e:
            # tri-state: errored → not_judged, NOT cached (retry next time), never 'judged false'
            return {"verdict": "abstain", "not_judged": True, "confidence": 0.0,
                    "reason": "judge_error:%s" % type(e).__name__}
        cache.put(k, r)
        return r
    return wrapped


def with_retry(judge: Callable, retries: int = 2, backoff: float = 0.0, sleep=time.sleep):
    """Retry a judge on exception (transient API failures). `sleep` injectable so tests don't wait.
    After `retries`, raises — let the caller's fail-safe (the Check / cached wrapper) turn it into
    not_judged/abstain."""
    def wrapped(claim_text: str, evidence_texts: List[str]) -> dict:
        last = None
        for attempt in range(retries + 1):
            try:
                return judge(claim_text, evidence_texts)
            except Exception as e:  # noqa: BLE001
                last = e
                if attempt < retries and backoff:
                    sleep(backoff * (attempt + 1))
        raise last
    return wrapped


def make_chunked_batch_judge(batch_judge: Callable[[List[Tuple[str, List[str]]]], List[dict]], chunk_size: int = 8):
    """`batch_judge`: list of (claim, evidence_texts) -> list of verdicts (same order/length). Returns
    a run_many(items) that chunks internally and caps blast radius — a chunk that raises (or returns
    the wrong length) yields not_judged for its claims only, not the whole set."""
    def run_many(items: List[Tuple[str, List[str]]]) -> List[dict]:
        out: List[dict] = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            try:
                res = batch_judge(chunk)
                if len(res) != len(chunk):
                    raise ValueError("batch judge returned %d verdicts for %d claims" % (len(res), len(chunk)))
                out.extend(res)
            except Exception as e:  # noqa: BLE001
                out.extend([{"verdict": "abstain", "not_judged": True, "confidence": 0.0,
                             "reason": "chunk_error:%s" % type(e).__name__}] * len(chunk))
        return out
    return run_many


def make_multi_lens_judge(judge, lenses, survival: str = "unanimous"):
    """Re-judge a span under N LENS FRAMINGS and combine — perspective-diverse verification (the
    fides-shaped half of noesis's lens technique). Returns an EntailmentJudge-shaped verdict; it
    NEVER drops (the policy table owns that). A 'violated' from ANY lens always wins (escape-safe).

    survival, applied only when no lens said 'violated':
      'unanimous' (DEFAULT): 'supported' iff EVERY lens supports — adversarial CONFIRMATION, lowers
                  fabrication-escape (a single framing's rubber-stamp can't carry it alone). Ships by
                  default because escape ≈ 0 is fides's non-negotiable invariant.
      'majority' : 'supported' iff a strict majority support.
      'any'      : 'supported' iff ANY lens supports — a RECALL move, but ESCAPE-UNSAFE (a fabrication
                  every-lens-but-one merely abstains on slips through). Opt-in; prove it with the P/R
                  harness (escape must stay 0) before relying on it.

    A 'lens' is a framing string prepended to the claim (the injected judge sees the same
    (claim, evidence)). Per-lens verdicts ride in `reason` (Rule 13). If the base judge is wrapped
    with make_cached_judge, each (claim, evidence, lens) memoizes independently — cost is N× first
    time only. Fail-safe: a lens whose judge errors/abstains is just an 'abstain' vote."""
    lenses = list(lenses)
    if not lenses:
        raise ValueError("make_multi_lens_judge needs at least one lens")
    if survival not in ("unanimous", "majority", "any"):
        raise ValueError("survival must be unanimous|majority|any")

    def wrapped(claim_text: str, evidence_texts) -> dict:
        votes = []
        for lens in lenses:
            framed = "[Judge under this lens: %s]\n%s" % (lens, claim_text)
            try:
                votes.append(judge(framed, evidence_texts).get("verdict", "abstain"))
            except Exception as e:  # noqa: BLE001 — a lens failure is one abstain vote, never a raise
                votes.append("abstain")
        reason = "; ".join("L%d=%s" % (i + 1, v) for i, v in enumerate(votes))
        if "violated" in votes:
            final = "violated"
        elif survival == "any":
            final = "supported" if "supported" in votes else "abstain"
        elif survival == "majority":
            final = "supported" if sum(v == "supported" for v in votes) * 2 > len(votes) else "abstain"
        else:  # unanimous
            final = "supported" if all(v == "supported" for v in votes) else "abstain"
        return {"verdict": final, "confidence": 1.0 if final != "abstain" else 0.0,
                "reason": reason, "lens_verdicts": votes}
    return wrapped
