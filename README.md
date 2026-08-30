<div align="center">

# fides

**A domain-agnostic faithfulness engine — keep only what's true to the source.**

*Catch fabricated numbers, misattributed quotes, over-generalizations, and misinterpretations in AI‑generated content **before** it's published — dropping only what's fabricated, never what's genuine.*

Zero runtime dependencies · Python ≥ 3.9 · deterministic core · 118 tests · TS↔Py golden parity

</div>

---

## The problem

An LLM writes a paragraph, a marketing post, an infographic. It reads fluently. Buried in it: a number that appears in **no** source, a real number pinned to the **wrong** company, a `100 mg` dose rendered as `100 mcg`, a quote put in the wrong mouth, a hedge inflated into a superlative. A human reviewer misses it because it *looks* right.

`fides` is the gate that sits between "generated" and "published." It doesn't grade style and it doesn't guess — it **verifies each claim against the typed source** and makes a publish decision you can defend, with an audit trail for every figure.

> **The one immovable rule.** A *proven* fabrication (a deterministic `false`) is **always dropped** — no config dial can override it. The dials only govern how strict we are about *true‑but‑uncited* general knowledge. Style is never a faithfulness axis.

---

## What it does, in one call

```python
from fides import Gate, NumericCheck, EntailmentCheck, format_gate_report

gate = Gate(checks=[NumericCheck(), EntailmentCheck(judge=my_judge)])
print(format_gate_report(gate.run(spans)))
```

```text
Gate verdict — 2/4 spans published, 2 withheld  {'keep': 2, 'drop': 1, 'hold': 1}
  ✓ [keep] s1
  ✓ [keep] s2
  ✗ [drop] s3  (numeric: unbound)          ← a number in no source cell: fabrication, DROPPED
  ✗ [hold] s4  (entailment: unsupported superlative/claim)   ← "best fund ever": HELD for review
```

Two genuine claims ship; the fabricated number is dropped; the unsupported superlative is held. Run it yourself: `python3 examples/quickstart.py` (no API key).

---

## How it works — the pipeline

Content comes in as **spans** (one claim each). Every span is routed to the **Checks** that can judge it; each Check emits **Findings** in one shared vocabulary; a **policy table** turns findings into a single publish decision per span. Nothing is bespoke per span — the decision logic is uniform.

```mermaid
flowchart LR
    A["Generated content<br/>(spans: one claim each)"] --> G{{"Gate<br/>orchestrator"}}
    S["Typed source<br/>(Fact cells:<br/>value·unit·entity·period)"] --> G

    G -->|numeric claims| N["NumericCheck<br/><i>deterministic</i>"]
    G -->|text + evidence| E["EntailmentCheck<br/><i>llm-judge</i>"]
    G -->|attribution/scope| C["CongruenceCheck<br/><i>llm-judge</i>"]
    G -->|verbatim quotes| Q["QuoteCheck<br/><i>deterministic</i>"]

    N --> F["Findings<br/>(shared verdict currency)"]
    E --> F
    C --> F
    Q --> F

    F --> P["Policy table<br/>(surface-aware)"]
    P --> D["Publish decision<br/>keep · hold · drop"]
    P --> AU["Source-documentation<br/>audit"]

    style N fill:#dcfce7,stroke:#16a34a,color:#000
    style Q fill:#dcfce7,stroke:#16a34a,color:#000
    style E fill:#e0f2fe,stroke:#0284c7,color:#000
    style C fill:#e0f2fe,stroke:#0284c7,color:#000
    style D fill:#fef9c3,stroke:#ca8a04,color:#000
```

**Green = deterministic** (a proof; can drop). **Blue = llm-judge** (an opinion; never auto-drops — it holds or flags). That distinction is the backbone of the whole system.

### The two kinds of verdict

| | Deterministic | LLM‑judge |
|---|---|---|
| Example | numeric ledger, quote gate | entailment, congruence, slop |
| A `false` means | a **proof** of fabrication | an **opinion** it's unsupported |
| On `false` | **always drops** (immovable) | **never auto-drops** — holds/flags |
| Fails safe by | typed mismatch → drop | abstaining (unavailable judge ≠ guilty) |

---

## The verdict currency: `Finding`

Every Check, however different inside, speaks one language. That's what lets one policy table decide everything.

| field | values | role |
|---|---|---|
| `dimension` | numeric · entailment · congruence · quote · slop | which Check produced it |
| `kind` | deterministic · llm_judge | proof vs opinion (governs whether it can drop) |
| `groundedness` | in_corpus · true_uncited · false · abstain | **surface‑invariant** label |
| `severity` / `confidence` | low·med·high / float | how strong |
| `source_locators` | [(snapshot, block, row, col), …] | the audit trail |

```mermaid
flowchart LR
    F["Finding<br/>(labeled once)"] --> P["Policy table<br/>(dimension × surface)"] --> D["keep · hold · drop"]
    style D fill:#fef9c3,stroke:#ca8a04,color:#000
```

`groundedness` is **surface‑invariant** — a claim is labeled once (is it in the corpus? true but uncited? false? unknowable?), and the **surface** (compliance vs marketing vs internal) decides the *consequence* as pure policy. The same fabrication drops on every surface; a true‑but‑uncited aside might hold on a compliance doc and pass on a blog. One label, many policies — no re-judging.

---

## The deterministic heart: the Numeric Ledger

This is what makes `fides` more than "does the number's text appear in the source." Instead of substring/n‑gram matching, it **types every quantity** and verifies the *meaning*.

```mermaid
flowchart TD
    R["emitted: '24%'  ·  binding: growth_pct(f2, f3)  ·  context: FundA"] --> PQ["parse → Quantity<br/>value · unit · magnitude · canonical"]
    PQ --> B{binding?}
    B -->|source| SRC["fetch the bound Fact cell"]
    B -->|derived| REC["recompute from operand cells"]
    B -->|unbound| FAB["no cell → FABRICATION"]
    SRC --> CH["congruence checks"]
    REC --> CO["operand coherence<br/>(same subject/period?)"] --> CH
    CH --> U{"unit congruent?<br/>(mg ≠ mcg, bps ≠ %)"}
    U -->|no| X["✗ drop"]
    U -->|yes| SU{"subject / period<br/>match?"}
    SU -->|no| X
    SU -->|yes| V{"value equal<br/>(rounding in display frame)?"}
    V -->|no| X
    V -->|yes| OK["✓ in_corpus"]
    FAB --> X

    style OK fill:#dcfce7,stroke:#16a34a,color:#000
    style X fill:#fee2e2,stroke:#dc2626,color:#000
    style FAB fill:#fee2e2,stroke:#dc2626,color:#000
```

It catches the failures a text-match misses — each is a real, adversarially‑tested case in `examples/proof.py`:

| Failure mode | Example | Verdict |
|---|---|---|
| **Fabrication** | a number in no source cell | drop |
| **Wrong‑but‑real cell** | a *peer's* return quoted as this fund's | drop |
| **Unit swap** | `100 mg` → `100 mcg` (1000× dose error); `65 bps` → `65%` | drop |
| **Period swap** | the 2024 figure labeled 2023 | drop |
| **Derived incoherence** | "growth" computed across two *different* subjects | drop |
| **Verbatim drift** | `12.4%` restated as `12.40%` under a strict surface | drop |
| **Genuine** | the right value, right cell, right period | **keep** |

Units, periods, and derivations are *computed structure* (code's job). Which company a value is *about*, whether a claim is *supported* — that's *meaning* (the LLM's job). fides never blurs the two.

---

## The other Checks

- **QuoteCheck** *(deterministic)* — a no‑fabrication span gate for verbatim quotes: exact → windowed fuzzy (`difflib ≥ 0.95`) → longest‑contiguous rebind (`≥ 70%`), with typography/whitespace normalization. Proves a quote actually exists in the source.
- **EntailmentCheck** *(llm‑judge)* — is this sentence entailed by its cited evidence? Injected judge returns `supported | violated | abstain`; fail‑safe to `abstain`.
- **CongruenceCheck** *(llm‑judge)* — attribution ("is this value about the right entity?") and over‑generalization ("does the claim over‑reach the evidence?").
- **Anti‑slop** *(separate quality track)* — AI‑cliché/filler phrases, empty sentences, hedge‑rate, low info density → a `slop_score`. **Slop is a usefulness axis, never a truth axis** — it's advisory and *subordinate* to faithfulness; a sloppy sentence is not a lie and is never dropped as a fabrication.

All judges are **injected**, never hardcoded — swap in `fides.adapters.openai_judge` for production, a deterministic stub for tests. An unavailable judge **abstains**; it never guesses guilt.

---

## From verifier to product: the Grounded Content Studio

The verifier flips around into a **generator**. `ContentStudio` brainstorms marketing assets from a customer's typed data — and because every number is gated by the ledger, deterministic assets are **grounded by construction** (an infographic literally cannot display a figure that isn't in the data), while an LLM‑drafted post has its fabrications dropped before it ships.

```mermaid
flowchart LR
    D["Customer data<br/>(typed Fact cells)"] --> BR["brainstorm ideas<br/>(post · image · video)"]
    BR --> CO["compose draft<br/>(deterministic or LLM)"]
    CO --> GA{{"Gate<br/>(ledger)"}}
    GA -->|all verified| SH["✓ shippable<br/>grounding = 100%"]
    GA -->|fabrication| WH["withhold span<br/>grounding &lt; 100%"]
    SH --> RN["render → real pixels"]
    RN --> SVG["infographic.svg"]
    RN --> HTML["storyboard.html<br/>(CSS-timed player, no ffmpeg)"]
    SH --> AUD["source-documentation<br/>audit per figure"]

    style SH fill:#dcfce7,stroke:#16a34a,color:#000
    style WH fill:#fee2e2,stroke:#dc2626,color:#000
```

`fides.render` turns the verified spec into **real, openable files with zero deps** — SVG posters and a self‑contained HTML video player — and *refuses to render an un‑shippable asset*, so grounding survives all the way to the canvas. Heavy rasterization (PNG/mp4) stays an injectable consumer adapter.

### Try the studio in your browser (no API key, stdlib only)

```bash
python3 examples/serve.py     # → open http://localhost:8000
```

Pick one of six preset datasets (finance · clinical · energy · SaaS · sports · elections) or enter your own; fides brainstorms a grounded post + infographic + video, renders them inline with a grounding score and per‑figure audit — then tick **"inject a fabricated stat"** and watch the gate drop it in real time.

---

## Tuning per use case: the Manifest

The engine is fixed; the *tuning surface* is a small `GateManifest`. One core, many verticals:

```mermaid
flowchart TD
    CORE["fides core<br/>(fixed logic)"]
    CORE --> M1["Medical manifest<br/>vocab: mg·IU·mcg<br/>strict compliance surface"]
    CORE --> M2["Deep-tech manifest<br/>vocab: nm·GHz·$<br/>authority pyramid"]
    CORE --> M3["Marketing manifest<br/>vocab: %·$·crore/lakh<br/>looser policy, slop-aware"]
```

The manifest carries: unit vocabulary, the policy table, confidence floor, which surfaces are strict/verbatim/period‑required, and which dimensions are enabled. A legal or financial vertical reuses the core untouched — it only ships a new manifest.

---

## Precision/recall harness — proving "keep genuine, drop fabricated"

fides is measured, not asserted. `harness.py` scores a labeled gold set on a **`dimension × surface‑tier`** matrix with **Wilson confidence intervals**. The ship‑gate is explicit:

- **fabrication‑escape rate → must be 0** (nothing false gets through), and
- **genuine‑recall → maximized** (we don't throw away true content).

`examples/proof.py` runs this end‑to‑end across 6 domains: all grounded assets ship at 100%, and a 13‑case adversarial battery drops **7/7 fabrications with 0 escapes and no genuine loss**.

---

## Cross‑language conformance

The numeric calculus has a TypeScript twin (its origin in `novelfusion`). `goldens/numeric_golden.json` is a **language‑neutral vector corpus** (34 cases) that both implementations must satisfy byte‑for‑byte, so the Python core and the TS twin can never silently diverge.

---

## Install & layout

Zero dependencies — copy the package in, or:

```bash
pip install -e .        # editable, from the repo root
python3 -m pytest -q    # 118 tests
```

```text
fides/
  finding.py     verdict currency + surface policy table (the one immovable rule)
  gate.py        orchestrator: spans → checks → findings → one decision + audit
  manifest.py    per-use-case tuning surface (unit vocab, policy, strict surfaces)
  numeric/       the deterministic ledger — parse · canonicalize · recompute · congruence · audit
  semantic/      entailment · congruence · robust judge wrappers (cache/retry/chunk/multi-lens)
  text/          QuoteCheck + fuzzy span verification (absorbed from factra)
  slop.py        anti-slop quality track (separate from truth)
  quality.py     tripwires: value-leak audit, goodhart, hedge lexicon
  studio.py      grounded content studio (brainstorm → ground → rank)
  render.py      verified spec → SVG / HTML pixels (zero-dep)
  generate.py    GroundedGenerator: plan → draft → verify → repair
  harness.py     precision/recall harness (Wilson CIs)
  adapters/      injectable OpenAI judges
goldens/         cross-language conformance vectors (TS↔Py parity)
examples/        quickstart · studio · serve (UI) · proof · multi_lens · end_to_end
```

---

## Examples

| File | What it shows |
|---|---|
| `examples/quickstart.py` | verify a mini answer with one `Gate` call (no key) |
| `examples/serve.py` | the browser studio UI (stdlib `http.server`, 6 preset domains) |
| `examples/studio.py` | brainstorm + ground + render posts/infographics/videos to real files |
| `examples/proof.py` | 6-domain grounded production + 13-case adversarial gate (escapes = 0) |
| `examples/multi_lens.py` | perspective-diverse judging + the harness A/B that gates it |
| `examples/end_to_end.py` | all subsystems exercised on one scenario |

---

## Design principles (why it's built this way)

1. **Code owns structure; the model owns meaning.** Units, periods, derivations, IDs → code. Attribution, relevance, interpretation → LLM. Neither is allowed to do the other's job.
2. **Deterministic proofs drop; opinions hold.** Only a proof can silently remove content; a judge's `false` escalates to review.
3. **Generation is a layer, never the core.** The verifier is the invariant; drafters, ideators, renderers are injected.
4. **Label once, apply as policy.** Surface‑invariant groundedness + a policy table — no per‑surface re‑judging.
5. **Fail safe.** An unavailable judge abstains; an uncheckable span holds. Never fail open.
6. **Measured, not asserted.** Every claim of correctness is backed by the harness or a golden vector.
```
python3 -m pytest -q
```
