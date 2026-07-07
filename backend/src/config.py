from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# backend/src/config.py -> backend/ -> repo root
BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

load_dotenv(REPO_ROOT / ".env")

# Legacy alias used in a few imports
PROJECT_ROOT = REPO_ROOT

SHOEBOX_DIR = REPO_ROOT / "shoebox"
RECEIPTS_DIR = SHOEBOX_DIR / "receipts"
STATEMENT_PATH = SHOEBOX_DIR / "card_statement.pdf"
INVOICES_PATH = SHOEBOX_DIR / "invoices.xlsx"
NOTES_PATH = SHOEBOX_DIR / "notes.txt"
REPORTS_DIR = REPO_ROOT / "reports"
ANALYSIS_CACHE_DIR = REPO_ROOT / ".cache" / "ledgerlens"

DEFAULT_CURRENCY = "CAD"
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%b %d, %Y")
