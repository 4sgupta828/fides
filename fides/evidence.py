"""Origin-scoped evidence resolution — the cross-tenant/cross-corpus FALSE-PASS guard (absorbed from
factra verify.py:579-611). Resolve a source by its ORIGIN KEY, never a bare id: numeric/string ids
collide across corpora and tenants, so a bare-id lookup can verify a claim against ANOTHER tenant's
document. An unresolved origin returns None (drop the claim) and NEVER falls back to another origin.
"""
from __future__ import annotations
from typing import Dict, Optional


class OriginScopedEvidence:
    def __init__(self):
        self._by_origin: Dict[str, Dict[str, dict]] = {}

    def add(self, origin: str, fact_id: str, fact: dict) -> None:
        self._by_origin.setdefault(origin, {})[fact_id] = fact

    def get(self, origin: str, fact_id: str) -> Optional[dict]:
        bucket = self._by_origin.get(origin)
        if bucket is None:
            return None  # unknown origin → DROP; never a cross-origin fallback (the false-pass guard)
        return bucket.get(fact_id)

    def facts_for(self, origin: str) -> Dict[str, dict]:
        """The facts_by_id map for ONE origin — pass this to a check's evidence, never a merged map."""
        return dict(self._by_origin.get(origin, {}))

    def origins(self):
        return list(self._by_origin.keys())
