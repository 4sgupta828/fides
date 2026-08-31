# I built 7 AI systems across 7 industries. They're all the same bet.

*A kickoff to a 7-part series. Each part goes deep on one system; this is the thesis that connects them.*

---

Over the last stretch I've built seven AI systems in seven different domains — a faithfulness engine, a clinical research assistant, a VC-diligence engine, a people-search graph, an autonomous SRE agent, an incident-simulation benchmark, and a governed content system.

They look unrelated. They're not. Every one of them is a bet on the same idea, and I think it's the most important idea in applied AI right now:

> **Fluency is commoditized. The moat is verification the model isn't allowed to overrule.**

Frontier models already write, reason, and summarize better than most humans. That capability is now a utility — you rent it by the token. So the defensible product is no longer "an AI that sounds smart." In every domain where being wrong is *expensive* — medicine, finance, reliability, compliance, hiring — the product is an AI whose **failures degrade to honesty instead of confident fabrication.** And you cannot get there by making the model bigger. You get there by architecture.

## The pattern, in three moves

After building the seventh one, the shared blueprint is impossible to unsee:

**1. Draw a hard line: code owns structure, the model owns meaning.**
The single most common failure I see in AI products is asking the model to do a job that belongs to code. Whether `65 bps == 0.65%`, whether a quote physically exists in a source, whether two company records are the same entity, whether metric A caused metric B — these are *computations and proofs*, not judgments. The moment you hand them to an LLM, you've re-introduced the exact failure you were trying to prevent. Meaning — is this relevant? does this follow? is this on-brand? — is the model's job, and it's genuinely good at it. Neither side does the other's job. Ever.

**2. Put a gate between the model and the reader that the model cannot talk its way past.**
Five of these seven systems literally share the same crown jewel: a *deterministic* check that a claim's cited quote exists, verbatim, in the source it points to — fail-closed, tenant-isolated, unfabricatable. It's almost dumb. That's the point. A substring check can't be charmed by a confident model the way an "are you sure?" prompt can. Everything clever — retrieval, reasoning, generation — sits *upstream* of the gate and can only *propose* candidates the gate then filters. No recall trick can weaken it.

**3. Measure the thing honestly enough that your own eval finds your bugs.**
Anyone can claim "zero hallucinations." The engineering question is *how do you know, and could you be fooled?* The systems that work ship an adversarial, held-out measurement harness — and it earns its keep. One of them (the faithfulness engine) caught a real safety bug in *itself*: a parser was treating `100 mg` and `100 mcg` as equal — the exact 1000× dose error that could hurt someone — and the eval flagged it before any human would have. That loop, an eval adversarial enough to find your own mistakes, is the difference between a demo and a product you'd stake a regulated business on.

## Seven systems, one bet

| # | System | Domain | The hard thing it refuses to fake |
|---|---|---|---|
| 1 | **Fides** | Cross-domain faithfulness | A number that's real but from the *wrong cell* (unit/period/entity/derivation) |
| 2 | **Noesis** | Clinical decision support | A confident fabrication that looks identical to a correct answer |
| 3 | **Eigen** | VC / deep-tech diligence | Reasoning laundered as fact; sentiment dressed up as a filing |
| 4 | **Roster** | People & company graph | A fabricated person/edge — and a *false merge* that poisons every count |
| 5 | **OATS** | Autonomous SRE / RCA | A confidently-wrong root cause (correlation sold as causation) |
| 6 | **Dataraft** | RCA benchmark / simulation | Grading yourself when you never actually know the true answer |
| 7 | **NovelFusion** | Governed content ops | A brand rule that reads well but silently corrupts unrelated content |

Different industries, different data, different failure surfaces. Identical spine: **the model interprets; deterministic code guarantees; an honest eval keeps everyone accountable.**

## Why this is the bet worth making

The last mile of enterprise AI is not a smarter model — it's *trust you can defend to a regulator, a clinician, a partner, or a board.* That trust doesn't come from the generator. It comes from the verifier the generator can't overrule, and from measurement honest enough to admit what's still broken.

Over the next seven posts I'll go deep on each system — the mechanism, the tradeoffs, where I drew the AI-vs-code line and why, how I measured that it works, and what's still genuinely hard (attribution ≠ correctness, the sim-to-real gap, entity resolution at scale, inference-provenance, latency). No hand-waving. The code is public.

If you're building AI for a domain where being wrong is expensive, I think you're going to end up at this same architecture — so let's compare notes.

**Part 1 drops next: Fides — engineering faithfulness into AI.** Follow along.

*(All seven are open source. Links in the comments.)*

**#AI #LLM #TrustworthyAI #RAG #AIGovernance #MLOps #ProductManagement #AIAgents**
