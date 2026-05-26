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
FUZZY_MATCH_THRESHOLD = 75
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%b %d, %Y")

MERCHANT_CATEGORIES = {
    "starbucks": "Food & Beverage",
    "tim hortons": "Food & Beverage",
    "cafe": "Food & Beverage",
    "restaurant": "Food & Beverage",
    "petit dep": "Food & Beverage",
    "uber": "Travel",
    "waymo": "Travel",
    "vrbo": "Travel",
    "parking": "Travel",
    "amazon": "Office Supplies",
    "staples": "Office Supplies",
    "postes": "Office Supplies",
    "art supply": "Office Supplies",
    "pharmacy": "Health",
    "adobe": "Software & Cloud",
    "google": "Software & Cloud",
    "canva": "Software & Cloud",
    "shopify": "Software & Cloud",
    "namecheap": "Software & Cloud",
    "chatgpt": "Software & Cloud",
    "openai": "Software & Cloud",
    "netflix": "Personal",
    "petco": "Personal",
    "brightpath": "Revenue",
    "greenloop": "Revenue",
    "nonna": "Revenue",
    "atelier": "Revenue",
    "bloom": "Revenue",
    "client payment": "Revenue",
    "consulting": "Revenue",
    "refund": "Revenue",
}
