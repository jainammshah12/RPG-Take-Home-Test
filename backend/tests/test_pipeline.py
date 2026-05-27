import pandas as pd

import src.pipeline as pipeline_mod
from src.config import SHOEBOX_DIR
from src.pipeline import run_pipeline


class _StubResult:
    def __init__(self, parsed: dict[str, pd.DataFrame]):
        self.parsed = parsed


def test_run_pipeline_uses_parsed_frames(monkeypatch):
    """Smoke-test the pipeline without calling external OCR/LLM services."""

    def fake_parse_all(_ingested):
        # Minimal parsed dict: just a couple of statement and invoice rows.
        return {
            "receipts": pd.DataFrame(),  # avoid calling external OCR
            "statement": pd.DataFrame(
                [
                    {
                        "source": "statement",
                        "source_file": "card.pdf",
                        "date_raw": "2025-03-10",
                        "merchant_raw": "STAPLES #0312",
                        "amount": -45.99,
                    }
                ]
            ),
            "invoices": pd.DataFrame(
                [
                    {
                        "source": "invoice",
                        "invoice_id": "INV-1",
                        "date_raw": "2025-03-01",
                        "merchant_raw": "BrightPath Marketing",
                        "amount": 3500.0,
                        "status": "paid",
                        "source_file": "invoices.xlsx",
                    }
                ]
            ),
            "notes": pd.DataFrame(),
        }

    monkeypatch.setattr(pipeline_mod, "parse_all", fake_parse_all)

    result = run_pipeline(shoebox_dir=SHOEBOX_DIR, generate_report=False)

    assert not result.transactions.empty
    assert "category" in result.transactions.columns
    assert "OFFICE_SUPPLIES" in set(result.transactions["category"])
    assert result.analytics is not None
    assert result.validation is not None
    assert result.report_path is None


def test_run_pipeline_generates_report_when_requested(monkeypatch, tmp_path):
    """PDF generation is opt-in via generate_report=True."""

    def fake_parse_all(_ingested):
        return {
            "receipts": pd.DataFrame(),
            "statement": pd.DataFrame(
                [
                    {
                        "source": "statement",
                        "source_file": "card.pdf",
                        "date_raw": "2025-03-10",
                        "merchant_raw": "STAPLES",
                        "amount": -45.99,
                    }
                ]
            ),
            "invoices": pd.DataFrame(),
            "notes": pd.DataFrame(),
        }

    fake_pdf = tmp_path / "report.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(pipeline_mod, "parse_all", fake_parse_all)
    monkeypatch.setattr(
        pipeline_mod,
        "generate_pdf_report",
        lambda *a, **k: fake_pdf,
    )

    result = run_pipeline(shoebox_dir=SHOEBOX_DIR, generate_report=True)
    assert result.report_path == fake_pdf

