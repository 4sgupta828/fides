"""faithful-core numeric Check — the deterministic verification calculus + audit."""
from . import ledger
from .check import NumericCheck
from .audit import build_audit_report, render_audit_markdown
