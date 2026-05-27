from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from src.output.export import build_pdf_report


def test_build_pdf_report_returns_none_when_invalid():
    result = MagicMock()
    result.validation = MagicMock(valid=False)
    result.analytics = MagicMock()

    assert build_pdf_report(result) is None


def test_build_pdf_report_generates_file(tmp_path, monkeypatch):
    result = MagicMock()
    result.validation = MagicMock(valid=True)
    result.analytics = MagicMock()
    result.transactions = pd.DataFrame(
        [{"source": "statement", "merchant": "Test", "amount": -10.0, "date": "2025-01-01"}]
    )
    result.parsed = {"receipts": pd.DataFrame()}

    fake_path = tmp_path / "report.pdf"
    monkeypatch.setattr(
        "src.output.export.generate_pdf_report",
        lambda *a, **k: fake_path,
    )

    path = build_pdf_report(result)
    assert path == fake_path
