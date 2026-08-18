#!/usr/bin/env python3
"""GATED live validation of the OpenAI judges against the held-out semantic gold set.

Runs ONLY if OPENAI_API_KEY is set. Tiny by design (~8 gpt-4o-mini calls, well under a cent) — this
is the panel's "evaluate the judge before trusting it" discipline. NOT part of the unittest suite, so
normal test runs never spend. Usage:  python3 scripts/validate_judges_live.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

if not os.environ.get("OPENAI_API_KEY"):
    print("OPENAI_API_KEY not set — skipping live validation. (Mock tests cover the adapter offline.)")
    sys.exit(0)

from faithful_core.adapters.openai_judge import make_openai_entailment_judge
from faithful_core.semantic_eval import run_entailment_eval, format_entailment_eval

cases = json.load(open(os.path.join(os.path.dirname(HERE), "goldens", "semantic_gold.json")))["cases"]
model = os.environ.get("FAITHFUL_JUDGE_MODEL", "gpt-4o-mini")
print("Running %d entailment cases on %s (est. < $0.001)...\n" % (len(cases), model))
report = run_entailment_eval(make_openai_entailment_judge(model=model), cases)
print(format_entailment_eval(report))
sys.exit(0 if report["accuracy"] >= 0.75 else 1)
