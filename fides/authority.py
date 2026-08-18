"""Deterministic authority / lifecycle FLOOR — the STRUCTURAL half of factra's proposed≠approved
guard (verify.py:75-103). The split respects Rule 18: code owns the STRUCTURAL fact — what grade is
the cited evidence, a computable property of its source class (application vs order, pending vs
granted, press-release vs audited-filing). The SEMANTIC call — is the claim asserting a *realized*
state the proposal-grade evidence can't support — belongs to the LLM (CongruenceCheck.kind_ok, whose
prompt already covers 'state intent as realized fact'). No keyword heuristic for meaning here.

Source-class → grade is domain vocabulary, supplied per vertical via the manifest (regulatory:
application/testimony=proposal, order/tariff=realized; patents: pending=proposal, granted=realized;
tech: press_release/beta=proposal, GA/audited=realized)."""
from __future__ import annotations
from typing import Iterable


def all_proposal_grade(source_classes: Iterable[str], proposal_classes) -> bool:
    """True iff there ARE cited source classes and EVERY one is proposal-grade. Conservative: an
    unknown/mixed class set returns False (do not floor). A True here means a claim asserting a
    realized status cannot be authority-supported — hand that to the modality judge to confirm."""
    classes = list(source_classes)
    return bool(classes) and all(sc in proposal_classes for sc in classes)
