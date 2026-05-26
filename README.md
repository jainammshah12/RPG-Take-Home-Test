# LedgerLens — Financial Intelligence

Ingest a **shoebox** of receipts, statements, invoices, and notes. Extract with Gemini vision (rotated/handwritten images), parse PDFs and Excel, reconcile, and explore insights in Streamlit.

## Supported inputs

| Type | Formats | Parser |
|------|---------|--------|
| Receipts | JPG, PNG, WEBP, GIF, BMP, TIFF | Gemini 2.0 Flash vision |
| Statements | Any PDF in `shoebox/` | pdfplumber (Visa/credit-card & table layouts) |
| Invoices | XLSX, XLS | pandas (flexible column names) |
| Notes | TXT, MD | Structured lines + Gemini + heuristics |

Receipt images may be **rotated 90°**, left/right aligned, crumpled, or handwritten — Gemini handles orientation in `receipt_ocr.py`.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# .env
GEMINI_API_KEY=your_key

streamlit run app.py
```

Use the **sidebar → Add documents** to upload more receipts, statements, invoices, or notes at any time, then click **Refresh analysis**.

## Shoebox layout

```
shoebox/
├── receipts/          # any supported image
├── Visa_Statement_Q12025.pdf   # any *.pdf at root
├── invoices.xlsx
└── notes.txt
```

## Pipeline

```
INGEST → PARSE → CLEAN → ENRICH → VALIDATE → ANALYTICS → Dashboard + PDF
```

## Environment

- Python 3.11+
- `GEMINI_API_KEY` in `.env` (required for receipt extraction; optional for unstructured notes)
