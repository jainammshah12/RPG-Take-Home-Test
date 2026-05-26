import pandas as pd

from src.enrichment.categorizer import categorize
from src.enrichment.reconciler import reconcile_invoices


def enrich(
    transactions: pd.DataFrame,
    parsed: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    df = categorize(transactions)
    df = reconcile_invoices(df, parsed.get("invoices", pd.DataFrame()))
    return df
