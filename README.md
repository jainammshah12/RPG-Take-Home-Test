# LedgerLens
### Turning a Financial Shoebox into Usable Insights
 
LedgerLens is a financial intelligence pipeline and dashboard for messy freelancer records — transforming a chaotic folder of documents into a clear, actionable overview.
 
---
 
## What It Does
 
**Input:** A "shoebox" of mixed financial records:
- Credit card statements (`.pdf`)
- Client invoices (`.xlsx`)
- Receipt images (`.jpg`, `.png`)
- Free-form notes (`.txt`, `.md`)

**Pipeline:** `INGEST → PARSE → CLEAN → VALIDATE → ANALYTICS → OUTPUT`

---
 
## Core Features
 
**Financial Overview**:  revenue, expenses, net cash flow, invoice status, merchant trends, and credit card breakdowns.
 
**Data Cleaning**: multi-format date parsing, currency normalization, merchant name cleaning, duplicate detection, and a unified transaction schema across all sources.
 
**Confidence-Aware Processing**: structured files are parsed deterministically; uncertain fields are surfaced rather than guessed.
 
**Interactive Dashboard** (Streamlit):
- KPI summaries and cash-flow charts
- Merchant and client analytics
- Receipt gallery with extracted metadata
- Unified transaction table with source tracking
- Validation alerts and PDF export

**Ask LedgerLens** — a scoped conversational assistant for querying your own data. Examples:
- *"What were my largest expenses in February?"*
- *"Which client generated the most revenue?"*
---
 
## Project Structure
 
```
src/
├── ingestion/
├── parsing/
├── cleaning/
├── validation/
├── analytics/
└── output/
```
 
Each stage is independently testable and designed for production-style modularity.
 
---
 
## Setup
 
```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
 
# 2. Install dependencies
pip install -r requirements.txt
```
 
Create a `.env` file in the project root:
 
```env
GEMINI_API_KEY=your_gemini_api_key_here
MINDEE_API_KEY=your_mindee_api_key_here
MINDEE_MODEL_ID=your_model_id_here
```
 
Add your documents to `shoebox/`:
 
```
shoebox/
├── receipts/
│   ├── receipt_1.jpg
│   └── receipt_2.png
├── Visa_Statement_Q12025.pdf
├── invoices.xlsx
└── notes.txt
```
 
```bash
# 3. Launch
streamlit run app.py
 
# 4. Run tests
pytest tests/
```
 
---
 
## Tech Stack
 
| Layer | Tools |
|---|---|
| Backend | Python, pandas, pdfplumber, openpyxl |
| OCR & AI | Mindee, Gemini API |
| Frontend | Streamlit |
| Testing | pytest |
 
---
 
## If I Had More Time
 
- **Smarter categorization**: accounting-style expense labels (Software, Travel, Meals, etc.) with model-assisted classification for ambiguous cases
- **Better explainability**: data quality scores, confidence fields, manual review queues
- **Productization**: persistent storage, multi-client workspaces, scheduled re-analysis, and a full financial copilot for bookkeeping exports
