from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.analytics.metrics import AnalyticsSummary, compute_analytics
from src.cleaning.normalizer import combine_sources
from src.config import SHOEBOX_DIR
from src.enrichment.categorizer import assign_categories
from src.ingestion.loader import IngestedFiles, ingest
from src.output.pdf_report import generate_pdf_report
from src.parsing import parse_all
from src.validation.validator import ValidationResult, validate


@dataclass
class PipelineResult:
    ingested: IngestedFiles
    parsed: dict[str, pd.DataFrame] = field(default_factory=dict)
    transactions: pd.DataFrame = field(default_factory=pd.DataFrame)
    validation: ValidationResult | None = None
    analytics: AnalyticsSummary | None = None
    report_path: Path | None = None


def run_pipeline(shoebox_dir: Path | None = None, generate_report: bool = True) -> PipelineResult:
    result = PipelineResult(ingested=ingest(shoebox_dir or SHOEBOX_DIR))

    result.parsed = parse_all(result.ingested)
    result.transactions = assign_categories(combine_sources(result.parsed))

    result.validation = validate(result.transactions)
    result.analytics = compute_analytics(result.transactions, result.parsed)

    if generate_report and result.validation and result.validation.valid:
        result.report_path = generate_pdf_report(
            result.transactions,
            result.analytics,
            receipts=result.parsed.get("receipts"),
        )

    return result
