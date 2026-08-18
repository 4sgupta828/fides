"""Numeric verification calculus — the first shared, deterministic Check. Domain-agnostic: the
parse/canonicalize/compare/recompute/congruence logic is fixed; the unit VOCAB is manifest config.
Cross-language canonical behavior is pinned by goldens/numeric_golden.json (TS twin). Pure stdlib.
"""
from __future__ import annotations
import math, re, unicodedata
from typing import Optional, List, Dict

from ..manifest import UnitVocab, DEFAULT_VOCAB

_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_MAG_RE = re.compile(r"\d\s*([a-z]{1,8})\b")


def parse_quantity(raw: str, vocab: UnitVocab = DEFAULT_VOCAB) -> Optional[dict]:
    t = raw.strip(); low = t.lower()
    m = _NUM_RE.search(t)
    if not m:
        return None
    core = m.group(0).replace(",", "")
    try:
        value = float(core)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    dot = core.find("."); decimals = 0 if dot == -1 else len(core) - dot - 1

    magnitude = 1.0
    mm = _MAG_RE.search(low)
    if mm and mm.group(1) in vocab.magnitudes:
        magnitude = vocab.magnitudes[mm.group(1)]

    unit = {"kind": "unknown"}; scale = magnitude
    if re.search(r"\bbps\b|\bbasis points?\b", low):
        unit = {"kind": "percent"}; magnitude = 1.0; scale = 0.01
    elif "%" in low or re.search(r"\bpercent(age)?\b|\bpct\b", low):
        unit = {"kind": "percent"}; magnitude = 1.0; scale = 1.0
    else:
        sym = next((s for s in vocab.currencies if s in t), None)
        codem = re.search(r"\b(usd|eur|gbp|jpy|inr|cad|aud)\b", low)
        if sym:
            unit = {"kind": "currency", "code": vocab.currencies[sym]}
        elif codem:
            unit = {"kind": "currency", "code": codem.group(1).upper()}
        elif re.search(r"(?:^|\d)\s*x\b", low) or re.search(r":\s*1\b", low):
            unit = {"kind": "ratio"}
        elif re.search(r"\b(day|week|month|quarter|year)s?\b", low):
            b = re.search(r"\b(day|week|month|quarter|year)s?\b", low).group(1)
            unit = {"kind": "duration", "base": b}
        elif value == math.trunc(value) or magnitude > 1:
            unit = {"kind": "count"}

    return {"raw": t, "value": value, "unit": unit, "magnitude": magnitude,
            "canonical": value * scale, "scale": scale, "displayDecimals": decimals}


def units_congruent(a: dict, b: dict) -> bool:
    if a["kind"] == "unknown" or b["kind"] == "unknown":
        return False
    if a["kind"] != b["kind"]:
        return False
    if a["kind"] == "currency":
        return a.get("code") == b.get("code")
    return True


_REL = 1e-9


def values_equal(emitted: dict, source_canonical: float, rounding: bool = True) -> bool:
    e = emitted["canonical"]; s = source_canonical
    if abs(e - s) <= _REL * max(1, abs(s)):
        return True
    if not rounding:
        return False
    half = 0.5 * (10 ** -emitted["displayDecimals"]) * abs(emitted["scale"] or 1)
    return abs(e - s) <= half + _REL * max(1, abs(s))


_ARITY = {"identity": 1, "sum": "var", "difference": 2, "delta": 2, "growth_pct": 2,
          "share_of": 2, "ratio": 2, "product": 2, "quotient": 2, "annualize": 1}


def recompute(op: str, xs: List[float]) -> Optional[float]:
    ar = _ARITY[op]
    if ar != "var" and len(xs) != ar:
        return None
    if ar == "var" and len(xs) < 1:
        return None
    a = xs[0] if xs else None; b = xs[1] if len(xs) > 1 else None
    if op == "identity": return a
    if op == "sum": return sum(xs)
    if op == "difference": return a - b
    if op == "delta": return b - a
    if op == "growth_pct": return None if a == 0 else ((b - a) / a) * 100
    if op == "share_of": return None if b == 0 else (a / b) * 100
    if op in ("ratio", "quotient"): return None if b == 0 else a / b
    if op == "product": return a * b
    if op == "annualize": return a * 12
    return None


def result_unit_of(op: str, units: List[dict]) -> dict:
    first = units[0] if units else {"kind": "unknown"}
    all_same = len(units) > 0 and all(
        u["kind"] == first["kind"] and (u["kind"] != "currency" or u.get("code") == first.get("code"))
        for u in units)
    if op in ("growth_pct", "share_of"): return {"kind": "percent"}
    if op == "ratio": return {"kind": "ratio"}
    if op in ("identity", "annualize"): return first
    if op in ("sum", "difference", "delta"): return first if all_same else {"kind": "unknown"}
    if op in ("product", "quotient"): return first
    return {"kind": "unknown"}


_ARTICLES = {"the", "a", "an", "of", "for"}


def _norm(s: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKC", s or "").lower()).strip()


def subjects_match(a: str, b: str) -> bool:
    x = sorted(t for t in _norm(a).split(" ") if t and t not in _ARTICLES)
    y = sorted(t for t in _norm(b).split(" ") if t and t not in _ARTICLES)
    if not x or not y or len(x) != len(y):
        return False
    return x == y


def parse_period(raw: str) -> dict:
    s = raw.lower()
    years = [int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", s)]
    year = years[0] if years else None
    half = re.search(r"\bh([12])\b", s) or re.search(r"\b([12])h\b", s)
    q = re.search(r"\bq\s*([1-4])\b", s) or re.search(r"\b([1-4])q\b", s) or re.search(r"\bq([1-4])(?=\s|$)", s)
    if len(years) >= 2:
        return {"raw": raw, "kind": "range", "year": years[0], "year2": years[1]}
    if re.search(r"trailing|\bttm\b|\bltm\b|last twelve|rolling|\b\d{1,2}\s*m\b|\b\d{1,2}[- ]month", s):
        return {"raw": raw, "kind": "range", "year": year}
    if half:
        return {"raw": raw, "kind": "half", "h": int(half.group(1)), "year": year}
    if q:
        return {"raw": raw, "kind": "quarter", "q": int(q.group(1)), "year": year}
    if re.search(r"\bfy\b|fy\d{2,4}|fiscal|full[- ]?year|annual", s) and year:
        return {"raw": raw, "kind": "fy", "year": year}
    if re.search(r"as[- ]of", s):
        return {"raw": raw, "kind": "as_of"}
    if year:
        return {"raw": raw, "kind": "fy", "year": year}
    return {"raw": raw, "kind": "none"}


def _entity_congruence(ctx: dict, ent: dict) -> str:
    checked = False
    if ctx.get("subject") and ent.get("subject"):
        checked = True
        if not subjects_match(ctx["subject"], ent["subject"]):
            return "mismatch"
    ctx_metric = ctx.get("metric") or ctx.get("label")
    if ctx_metric and ent.get("metric"):
        checked = True
        if not subjects_match(ctx_metric, ent["metric"]):
            return "mismatch"
    return "match" if checked else "unchecked"


def _period_congruence(ctx_period: Optional[str], fp: dict) -> str:
    if not ctx_period or fp["kind"] == "none":
        return "unchecked"
    c = parse_period(ctx_period)
    if c["kind"] == "none":
        return "unchecked"
    if c["kind"] != fp["kind"]:
        return "mismatch"
    for k in ("year", "q", "h", "year2"):
        if c.get(k) is not None and fp.get(k) is not None and c[k] != fp[k]:
            return "mismatch"
    return "match"


_RAW_CORE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _emitted_raw_present(emitted_raw: str, source_text: str) -> bool:
    """Does the emitted number appear VERBATIM (standalone, un-normalized) in the source text? This
    is factra's locator cell re-read (verifier.py:134-137): $1.79 must NOT satisfy a source cell of
    $1.790 — the whole point is to catch that display drift / wrong-but-real sibling cell that the
    tolerant canonical calculus smooths over. Standalone boundary so 1.79 ≠ inside 1.790."""
    m = _RAW_CORE.search(emitted_raw)
    if not m:
        return False
    core = m.group(0).replace(",", "")
    hay = re.sub(r"\s+", " ", source_text).replace(",", "")
    return re.search(r"(?<![\d.])" + re.escape(core) + r"(?![\d])", hay) is not None


def _fail(code, bound=None):
    return {"ok": False, "code": code, "bound_fact_ids": bound or [], "emitted_canonical": None,
            "source_canonical": None, "locators": []}


def verify_claim(claim: dict, facts_by_id: dict, opts: dict, vocab: UnitVocab = DEFAULT_VOCAB) -> dict:
    strict = opts.get("strict", False); strict_period = opts.get("strict_period", False)
    verbatim = opts.get("verbatim", False)
    min_conf = opts.get("minConfidence", 0); rounding = opts.get("rounding", True)
    emitted = parse_quantity(claim["emitted"], vocab)
    if not emitted:
        return _fail("unparseable")
    b = claim["binding"]
    if b["kind"] == "unbound":
        return _fail("unbound")

    if b["kind"] == "derived":
        op = b["derivation"]["op"]; ids = b["derivation"]["operandFactIds"]
        ops = [facts_by_id.get(i) for i in ids]
        if any(f is None for f in ops):
            return _fail("derivation_unverifiable", ids)
        ar = _ARITY[op]
        if ar != "var" and len(ops) != ar:
            return _fail("derivation_unverifiable", ids)
        canon = recompute(op, [f["quantity"]["canonical"] for f in ops])
        if canon is None:
            return _fail("derivation_unverifiable", ids)
        runit = result_unit_of(op, [f["quantity"]["unit"] for f in ops])
        if not units_congruent(emitted["unit"], runit):
            return _fail("unit_mismatch", ids)
        if not values_equal(emitted, canon, rounding):
            r = _fail("derivation_mismatch", ids); r["emitted_canonical"] = emitted["canonical"]; r["source_canonical"] = canon; return r
        subs = [f["entity"]["subject"] for f in ops]
        if not all(subjects_match(s, subs[0]) for s in subs):
            return _fail("operands_incoherent", ids)
        if claim["context"].get("subject") and not subjects_match(claim["context"]["subject"], subs[0]):
            return _fail("entity_mismatch", ids)
        if min(f["confidence"] for f in ops) < min_conf:
            return _fail("low_confidence", ids)
        return {"ok": True, "code": "ok", "bound_fact_ids": ids, "emitted_canonical": emitted["canonical"],
                "source_canonical": canon, "locators": [f["locatorText"] for f in ops]}

    fact = facts_by_id.get(b["factId"])
    if not fact:
        return _fail("fact_missing", [b["factId"]])
    if not units_congruent(emitted["unit"], fact["quantity"]["unit"]):
        return _fail("unit_mismatch", [fact["id"]])
    if not values_equal(emitted, fact["quantity"]["canonical"], rounding):
        r = _fail("value_mismatch", [fact["id"]]); r["emitted_canonical"] = emitted["canonical"]; r["source_canonical"] = fact["quantity"]["canonical"]; return r
    ent = _entity_congruence(claim["context"], fact["entity"])
    if ent == "mismatch":
        return _fail("entity_mismatch", [fact["id"]])
    per = _period_congruence(claim["context"].get("period"), fact["period"])
    if per == "mismatch":
        return _fail("period_mismatch", [fact["id"]])
    cb = claim["context"].get("basis"); fb = fact["entity"].get("basis")
    if cb and fb and not subjects_match(cb, fb):
        return _fail("basis_mismatch", [fact["id"]])
    if fact["confidence"] < min_conf:
        return _fail("low_confidence", [fact["id"]])
    # VERBATIM (opt-in, e.g. table-cell surfaces): the emitted number must be the EXACT source string,
    # not merely canonically-equal — catches $1.79 vs $1.790 display drift / wrong sibling cell. Do
    # NOT enable on prose surfaces where legitimate rounding ($1.2B from $1,234,000,000) is expected.
    if verbatim and fact.get("locatorText") and not _emitted_raw_present(emitted["raw"], fact["locatorText"]):
        r = _fail("raw_mismatch", [fact["id"]]); r["emitted_canonical"] = emitted["canonical"]; return r
    if strict and ent == "unchecked":
        return _fail("entity_unresolved", [fact["id"]])
    # period-strictness is a SEPARATE opt-in knob (panel: too aggressive to auto-apply on compliance).
    if strict_period and per == "unchecked" and claim["context"].get("period") is None and fact["period"]["kind"] != "none":
        return _fail("period_unresolved", [fact["id"]])
    return {"ok": True, "code": "ok", "bound_fact_ids": [fact["id"]], "emitted_canonical": emitted["canonical"],
            "source_canonical": fact["quantity"]["canonical"], "locators": [fact["locatorText"]]}


def materialize_fact(g: dict, vocab: UnitVocab = DEFAULT_VOCAB) -> dict:
    return {"id": g["id"], "quantity": parse_quantity(g["value"], vocab),
            "entity": {"subject": g["subject"], "metric": g["metric"], "basis": g.get("basis")},
            "period": parse_period(g["period"]) if g.get("period") else {"raw": "", "kind": "none"},
            "confidence": g.get("confidence", 0.9), "locatorText": g.get("locatorText", "…%s…" % g["value"])}


def materialize_claim(c: dict) -> dict:
    return {"emitted": c["emitted"], "binding": c["binding"],
            "context": dict({"surface": "infographic"}, **(c.get("context") or {}))}
