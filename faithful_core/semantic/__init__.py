"""Semantic (llm_judge) checks — canonical in Python, invoked over the LLM boundary. The judge is
always INJECTED so the core has no provider dependency and stays fully testable without an API."""
from .entailment import EntailmentCheck, EntailmentJudge, abstaining_judge, VERDICTS
