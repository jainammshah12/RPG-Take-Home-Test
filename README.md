# LedgerLens: Financial Intelligence System
### Turning a Financial Shoebox into Usable Insights

LedgerLens is a financial intelligence pipeline and dashboard for messy freelancer records — transforming a chaotic folder of documents into a clear, actionable overview.

---

## Core Features
 
**Financial Overview**:  revenue, expenses, net cash flow, invoice status, merchant trends, and credit card breakdowns.
 
**Data Cleaning**: multi-format date parsing, currency normalization, merchant name cleaning, duplicate detection, and a unified transaction schema across all sources.
 
**Confidence-Aware Processing**: structured files are parsed deterministically; uncertain fields are surfaced rather than guessed.
 
**React dashboard** (Vite + FastAPI):
- KPI summaries and cash-flow charts
- Merchant and client analytics
- Receipt gallery with extracted metadata
- Unified transaction table with source tracking
- Validation alerts and PDF export

**Ask LedgerLens** — a simple scoped conversational assistant for querying your own data. Examples:
- *"What were my largest expenses in February?"*
- *"Which client generated the most revenue?"*
---

## Project Structure

```
backend/
  src/            # Pipeline + FastAPI (src.api.main)
  ├── api/        # REST API endpoints
  ├── cache/      # Database
  ├── ingestion/  # Obtain/Add Files 
  ├── parsing/    # Extract Information/Keywords
  ├── cleaning/   # Normalize Dates, Currency and Names
  ├── validation/ # Validate that Information is Cleaned
  ├── analytics/  # Dashboards/Visualizations
  ├── enrichment/ # Categorization Logic
  ├── output/     
  └── chat/         # Chat assistant (Groq)
  tests/
frontend/        # React + Vite UI
shoebox/         # Documents (repo root — not inside backend/)
```

---

## Setup

```bash
# 1. Python environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
MINDEE_API_KEY=your_mindee_api_key_here
MINDEE_MODEL_ID=your_model_id_here
```

### Run the app (React + API)

**Current terminal:**
```bash
cd backend
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

The Vite dev server proxies `/api` to the backend on port 8000.

## Data Flow

**Pipeline:** `INGEST → PARSE → ENRICH → CLEAN → VALIDATE → ANALYTICS → OUTPUT`

- The **React frontend** communicates with the **FastAPI backend** through `/api` (proxied to port `8000` during development).

- Expected Inputs include Credit card statements (`.pdf`), Client invoices (`.xlsx`), Receipt images (`.jpg`, `.png`), Free-form notes (`.txt`, `.md`)

- Uploaded files are sent as `multipart/form-data` and stored in the `shoebox/` folder.

- Each upload clears the in-memory session so the next analysis run picks up newly added files.

- On load or refresh, the frontend calls:

  ```http
  GET /api/analysis
  ```

- The backend optimizes processing through **session + disk caching**:
  - Checks an **in-memory session** first
  - Falls back to a **disk cache** keyed by shoebox path
  - Tracks file changes using a manifest of timestamps and file sizes
  - Reuses cached parsed results when nothing changes
  - Parses only **new or modified files incrementally**
  - Performs a full analysis only on first load or force refresh

- Parsed receipts, statements, invoices, and notes are then passed through the financial pipeline:

  ```text
  combine_sources → assign_categories → validate → compute_analytics
  ```

- The backend returns a structured JSON payload containing:
  - Transactions
  - Analytics and KPIs
  - Validation flags
  - Receipt metadata

- React stores this data in state and renders it across the application:
  - KPI cards and charts
  - Unified transaction table
  - Receipt gallery
  - Validation alerts

- Receipt images are served directly through:

  ```http
  GET /api/receipts/{filename}
  ```

- The chat assistant communicates with:

  ```http
  POST /api/chat
  ```

- Chat responses stay grounded in the **current dashboard analysis** by using a cached dashboard context rather than querying raw documents again.

### Tests

```bash
# Backend (from repo root)
pytest

# Frontend
cd frontend
npm test
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analysis` | Load or incrementally update analysis |
| POST | `/api/analysis/refresh` | Force full re-parse |
| POST | `/api/chat` | Ask LedgerLens assistant |
| POST | `/api/upload/receipts` | Upload receipt images |
| POST | `/api/upload/statement` | Upload statement PDF |
| POST | `/api/upload/invoices` | Upload invoice workbook |
| POST | `/api/upload/notes` | Append notes |
| GET | `/api/receipts/{filename}` | Receipt image |
| POST | `/api/export/pdf` | Download PDF report |

---

## Shoebox layout

```
shoebox/
├── receipts/
│   ├── receipt_1.jpg
│   └── receipt_2.png
├── Visa_Statement_Q12025.pdf
├── invoices.xlsx
└── notes.txt
```

---

## Tech Stack

| Layer | Tools |
|-------|--------|
| Backend | Python, FastAPI, pandas, pdfplumber, openpyxl |
| Frontend | React, TypeScript, Vite, Recharts |
| OCR | Mindee |
| Chat | Groq (Llama 3.3) |
| Testing | pytest, jest |
 
---
 
## If I Had More Time and GenAI Credits

- **Improved Extraction with LLMs**: Currently, the Mindee API, pdfplumber, pandas and Regex are doing well to parse the information. However, there are a lot of edge cases (especially for notes.txt) where a LLM can eliminate the ambiguity and give the right kind of answers for the existing data.
- **Improved Chat Feature with RAG**: With extra credits, I would improve the responses in the chat feature using RAG (Retrieval Augmented Generation) to respond with higher accuracy and precision to any possible query asked.
- **Persistent Database and Deployment**: With more time, I would expand scope to a lot of users where I can add an SQL persistent database instead of simple caching to process data and also deploy on Docker and Kubernetes to test how API endpoints and features work for a huge number of users.
- **Explainability Scores for the Data**: With additional time, I could add metrics such as data quality scores, confidence fields and manual review queues.

## Images

<img width="1896" height="862" alt="image" src="https://github.com/user-attachments/assets/7485f93c-b057-4dd1-b590-a4d598eab8a1" />
<img width="1508" height="862" alt="image" src="https://github.com/user-attachments/assets/9993cd3c-9f92-49d2-835d-e7bba03dc97c" />
<img width="1886" height="872" alt="image" src="https://github.com/user-attachments/assets/1f555a1c-1b5c-4ce9-b535-4243db827c91" />
<img width="1495" height="831" alt="image" src="https://github.com/user-attachments/assets/94c7fdfc-972c-4288-a74d-5f14f2bab5d1" />
<img width="922" height="505" alt="image" src="https://github.com/user-attachments/assets/6f062364-f931-458a-86a4-53b7943adddd" />

