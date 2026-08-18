"""OpenAI judge adapters — turn the injectable judge protocols into live LLM judges (a DIFFERENT
model family from a typical Anthropic drafter — judges should fail uncorrelated). Adopts the
Noesis/Eigen `_ENTAIL_SYSTEM` discipline: entailment (support, not topic-share) and congruence
(on_subject / kind_ok). Lazy import of `openai`, so the core package stays zero-dependency; only
using this module needs the SDK + a key. Fail-safe: any error/parse failure → abstain."""
from __future__ import annotations
import json
from typing import List, Optional

_ENTAIL_SYSTEM = (
    "You are a strict grounding auditor. Decide whether the EVIDENCE DIRECTLY SUPPORTS the CLAIM — "
    "not merely shares a topic. 'supported' = the evidence entails the claim; 'violated' = the "
    "evidence contradicts it OR the claim asserts a specific/superlative the evidence does not "
    "support; 'abstain' = you cannot tell. Judge faithfulness to the cited evidence, not truth in "
    "the world. When uncertain, abstain. Respond as JSON: "
    '{"verdict":"supported|violated|abstain","confidence":0.0-1.0,"reason":"short"}'
)

_CONGRUENCE_SYSTEM = (
    "You are a strict attribution auditor. For the CLAIM against its EVIDENCE decide two things: "
    "on_subject = is the claim about the SAME entity/subject the evidence is actually about (not a "
    "sibling/wrong entity)?  kind_ok = does the claim's assertion KIND match the evidence's kind "
    "(e.g. does it not broaden a single example into a general rule, or state intent as realized "
    "fact)? Each is 'supported'|'violated'|'abstain'; abstain when unsure. Respond as JSON: "
    '{"on_subject":"...","kind_ok":"...","confidence":0.0-1.0,"reason":"short"}'
)

_VERDICTS = ("supported", "violated", "abstain")


def _default_client():
    from openai import OpenAI  # lazy — only when a real judge is actually used
    return OpenAI()


def _chat_json(client, model: str, system: str, user: str, timeout: float = 30.0) -> dict:
    res = client.chat.completions.create(
        model=model, temperature=0, response_format={"type": "json_object"}, timeout=timeout,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return json.loads(res.choices[0].message.content or "{}")


def _fmt(claim_text: str, evidence_texts: List[str]) -> str:
    ev = "\n".join("- " + e for e in evidence_texts) or "(no evidence provided)"
    return "CLAIM:\n%s\n\nEVIDENCE:\n%s" % (claim_text, ev)


def _norm_verdict(v) -> str:
    return v if v in _VERDICTS else "abstain"


def make_openai_entailment_judge(model: str = "gpt-4o-mini", client=None, timeout: float = 30.0):
    """Returns an EntailmentJudge callable → {verdict, confidence, reason}."""
    def judge(claim_text: str, evidence_texts: List[str]) -> dict:
        try:
            data = _chat_json(client or _default_client(), model, _ENTAIL_SYSTEM, _fmt(claim_text, evidence_texts), timeout)
            return {"verdict": _norm_verdict(data.get("verdict")),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reason": str(data.get("reason", ""))}
        except Exception as e:  # fail-safe: abstain, never a guess
            return {"verdict": "abstain", "confidence": 0.0, "reason": "judge_error:%s" % type(e).__name__}
    return judge


def make_openai_congruence_judge(model: str = "gpt-4o-mini", client=None, timeout: float = 30.0):
    """Returns a CongruenceJudge callable → {on_subject, kind_ok, confidence, reason}."""
    def judge(claim_text: str, evidence_texts: List[str]) -> dict:
        try:
            data = _chat_json(client or _default_client(), model, _CONGRUENCE_SYSTEM, _fmt(claim_text, evidence_texts), timeout)
            return {"on_subject": _norm_verdict(data.get("on_subject")),
                    "kind_ok": _norm_verdict(data.get("kind_ok")),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reason": str(data.get("reason", ""))}
        except Exception as e:
            return {"on_subject": "abstain", "kind_ok": "abstain", "confidence": 0.0, "reason": "judge_error:%s" % type(e).__name__}
    return judge
