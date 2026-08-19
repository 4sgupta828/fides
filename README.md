# fides

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

## Multi-lens judging (perspective-diverse verification)
`make_multi_lens_judge(judge, lenses, survival='unanimous')` re-judges a span under N lens
framings and combines them — the fides-shaped half of noesis's lens technique. A 'violated'
from any lens always wins (escape-safe). Default **unanimous** = adversarial confirmation
(supported only if every lens agrees) → it *lowers* fabrication-escape; `any` is a recall move
but escape-unsafe (opt-in, prove with the harness first). It returns a verdict — it never
drops; the policy table still owns that. The P/R harness A/B gates it: escape must stay 0.

## Absorbed from factra (battle-tested)
- **QuoteCheck** — a deterministic, LLM-free no-fabrication span gate (3-tier: exact →
  windowed difflib ≥0.95 → longest-contiguous rebind ≥70%, with typography+whitespace
  normalization). Fills the `quote` dimension.
- **Prose value-leak audit** — a withheld number must not survive in the published text
  (`leaked_values`); polices currency/decimal/percent/bps only, never bare years/counts.
- **Fail-closed coverage** — a span with content but nothing that can verify it now abstains
  (compliance holds it) instead of silently publishing (was fail-open).

## Anti-slop (a SEPARATE quality track)
Slop is a *usefulness* axis, never a truth axis — a sloppy sentence isn't a lie, and the
faithfulness verifier never reaches into style. So `slop.py` measures it separately:
deterministic signals (AI-cliché/filler phrases, empty no-concrete-content sentences,
hedge-rate, low grounded-info density) → `slop_score` / `assess_slop`, an advisory field on
the `GateReport`, plus an optional injected LLM slop judge. It feeds the generation
**de-slop** pass (rewrite filler concrete) — which is SUBORDINATE to faithfulness: a
de-slopped rewrite must still pass the fabrication gate, or it's rejected. Slop never drops
content as a fabrication.

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

## Test
```
python3 -m unittest discover -s tests -v
```
