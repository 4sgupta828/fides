# Fides — Can we stop AI from lying with numbers?

*A LinkedIn post. Repo: https://github.com/4sgupta828/fides*

---

**The problem nobody wants to say out loud about "AI for the enterprise":**

The demo is beautiful. The pilot ships. And then a generated report says a fund returned **12.4%** when the source says the *benchmark* did, or renders a **100 mg** dose as **100 mcg**, or quietly inflates "the data suggests" into "the #1 solution, guaranteed." Every one of those reads perfectly. A human reviewer misses it because it *looks* right.

This is the real blocker to AI in regulated, high-stakes work — finance, healthcare, legal, compliance. Not "is the model smart enough?" but **"can I prove this sentence is true to the source before it's published?"** Fluency is solved. Faithfulness is not.

**What I explored: Fides — a domain-agnostic faithfulness engine.**

Instead of asking an LLM "is this hallucinated?" (asking the fox to guard the henhouse), Fides treats verification as a typed, deterministic problem wherever it can:

- Every number becomes a typed **quantity** — value, unit, entity, period — and is verified against the actual source cell, or *recomputed* from its operands. Substring matching says "12.4% appears in the source ✓." The ledger says "12.4% belongs to the benchmark, not this fund ✗."
- Every verdict speaks one currency: a **Finding**. Deterministic proofs can *drop* content; LLM-judge opinions can only *hold* it for review. That single distinction is the backbone.
- One immovable rule: a **proven** fabrication is always dropped — no config dial overrides it.

Then the whole thing runs *backwards* as a generator: brainstorm a post/infographic/video from a customer's data, and because every figure is gated, the asset is grounded **by construction** — it literally cannot render a number that isn't in the data.

**What AI solves well here:**
- Judging *meaning*: is this claim entailed by the evidence? is the quote attributed to the right person? is this an over-generalization? LLMs are genuinely good at this — as *judges*, not authors.
- Drafting, then repairing against a critic that hands back the exact reason.

**What AI does NOT solve — and shouldn't be asked to:**
- Structure and computation. Unit congruence, period matching, derivation recompute, IDs — that's *code's* job. The moment you ask a model to "check if 65 bps equals 0.65%," you've reintroduced the failure. Code owns structure; the model owns meaning; neither does the other's job.

**What stays genuinely hard:**
- The wrong-but-real cell. A number that exists in the source but answers a different question is the hardest class — provenance ("this string exists") is necessary but never sufficient for correctness.
- Measuring recall honestly: it's easy to drop everything and claim zero fabrications. The hard metric is *keep the genuine, drop only the fabricated* — which needs held-out, adversarial evals, not vibes.

**How to take it from here:**
- Wire real LLM judges over a clean tool boundary; keep the deterministic core language-neutral (Fides ships TS↔Python golden-vector parity so the calculus can't silently drift).
- Push the precision/recall harness into CI as a ship gate: fabrication-escape must stay at 0.
- Expand typed checks beyond numbers — dates, named entities, citations.

**Products this could become:**
- A "publish gate" API that sits between any GenAI system and its output surface.
- A grounded content studio for finance/pharma marketing where compliance is structural.
- A verification layer for RAG that catches the wrong-cell errors retrieval quality can't.

**To understand this space better, look up:** FActScore, RAGAS, SelfCheckGPT, TruthfulQA, Google's "Attributable to Identified Sources (AIS)", and the NLI/entailment literature. The throughline: attribution ≠ correctness.

The uncomfortable takeaway: **the last mile of enterprise AI isn't a better model. It's a verifier the model isn't allowed to overrule.**

#AI #LLM #Trustworthy​AI #RAG #Fintech #HealthcareAI #MLOps
