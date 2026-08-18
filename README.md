# faithful-core

A domain-agnostic **faithfulness engine**: verify that AI-generated content is *true to its source*
— catch fabricated numbers, misattributed quotes, over-generalizations, misinterpretations — before
it's published, and keep only what's genuine.

It is a **light platform**, not a heavy shared runtime (panel decision):

- a shared **verdict currency** — `Finding` (span + dimension + deterministic-vs-judge +
  surface-invariant `groundedness`) → a **policy table** → a publish decision (`finding.py`);
- a registry of **Checks** — `numeric-ledger` first (deterministic, typed value/unit/entity/period +
  derivation recompute); entailment/congruence/slop join later (llm-judge, canonical in Python);
- a per-use-case **manifest** — the small tuning surface (unit vocab, policy table, confidence floor,
  strict surfaces). Medical tunes `mg/IU`, deep-tech `nm/GHz/$`, marketing a looser policy;
- a **precision/recall harness** (`harness.py`) — a `dimension × surface-tier` matrix with Wilson CIs
  measuring "keep genuine, drop only fabricated";
- a language-neutral **golden-vector corpus** (`goldens/`) — the conformance contract that keeps the
  Python core and its TypeScript twin (novelfusion) byte-identical.

Zero runtime dependencies, Python ≥ 3.9 — drops into any consumer.

## The one immovable rule
A **deterministic `false`** — a *proven* fabrication — is **always dropped**; no policy dial can
override it. The dial ranges over *grounding strictness* (what happens to true-but-uncited general
knowledge), never over fabrication. Style is not a faithfulness axis and never enters the verifier.

## Roadmap
1. ✅ Contract (`Finding`) + numeric Check + golden-vector conformance (34 cases, TS↔Py parity).
2. ✅ First semantic Check stub — `EntailmentCheck` with an injectable judge (supported|violated|
   abstain), fail-safe, llm_judge policy (never auto-drops). Real OpenAI judge wired later.
3. ✅ CongruenceCheck (attribution + over-generalization) + anti-slop quality tripwires + a unified
   `Gate` orchestrator (one call → one publish verdict across all checks + audit + quality).
4. Wire the real OpenAI judges (entailment/congruence) over the LLM boundary (Python-canonical).
5. Land the numeric Check in one Python consumer behind a flag, displacing its n-gram number check;
   confirm held-out eval ≥ current.
6. ✅ Grounded-generation stub — `GroundedGenerator`: `plan → draft → verify(Gate) → repair`
   (verifier as critic; `Finding.reason` is the repair instruction). Injectable drafter/repairer.
7. Wire real LLM drafter/judges; land in a Python consumer; the video repair loop.
4. The marketing policy-table dial.
5. Generation *on top*: `plan → retrieve → draft → verify → repair` (the verifier as critic).

## Test
```
python3 -m unittest discover -s tests -v
```
