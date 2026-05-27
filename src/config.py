from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SHOEBOX_DIR = PROJECT_ROOT / "shoebox"
RECEIPTS_DIR = SHOEBOX_DIR / "receipts"
STATEMENT_PATH = SHOEBOX_DIR / "card_statement.pdf"
INVOICES_PATH = SHOEBOX_DIR / "invoices.xlsx"
NOTES_PATH = SHOEBOX_DIR / "notes.txt"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_CURRENCY = "CAD"
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%b %d, %Y")
