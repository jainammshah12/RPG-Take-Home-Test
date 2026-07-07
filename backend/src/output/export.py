from __future__ import annotations

"""On-demand export helpers."""

from pathlib import Path

from src.output.pdf_report import generate_pdf_report


def build_pdf_report(result) -> Path | None:
    """Generate a PDF report from a pipeline result. Returns None if validation fails."""
    if not result.validation or not result.validation.valid:
        return None
    if not result.analytics:
        return None
    return generate_pdf_report(
        result.transactions,
        result.analytics,
        receipts=result.parsed.get("receipts"),
    )
