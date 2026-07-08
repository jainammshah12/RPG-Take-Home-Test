"""LedgerLens REST API — serves the React frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.serialize import serialize_pipeline_result
from src.api.state import clear_analysis_keys, session
from src.cache.analysis_store import (
    analysis_needs_loading,
    get_analysis_result,
    invalidate_analysis_cache,
    shoebox_file_index,
)
from src.config import REPO_ROOT, SHOEBOX_DIR
from src.ingestion.uploads import append_notes, save_invoices, save_receipts, save_statement
from src.output.export import build_pdf_report
from src.chat.chat_assistant import generate_reply

app = FastAPI(title="LedgerLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "https://ledgerlens-pwnl.onrender.com/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _BytesFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str


def _resolve_shoebox(path: str | None) -> Path:
    if not path:
        return SHOEBOX_DIR.resolve()
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p.resolve()


def _load_analysis(shoebox: Path, *, force: bool = False):
    if force:
        invalidate_analysis_cache(shoebox)
        clear_analysis_keys()
    if analysis_needs_loading(shoebox, session, force=force):
        result, chat_context, load_info = get_analysis_result(shoebox, session, force=force)
    else:
        result, chat_context, load_info = get_analysis_result(shoebox, session, force=False)
    return result, chat_context, load_info


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {"default_shoebox": str(SHOEBOX_DIR.resolve())}


@app.get("/api/shoebox/summary")
def shoebox_summary(shoebox: str | None = Query(None)):
    path = _resolve_shoebox(shoebox)
    if not path.exists():
        return {"exists": False, "receipts": 0, "statements": 0, "invoices": 0}
    rc = len(list((path / "receipts").glob("*"))) if (path / "receipts").exists() else 0
    pdfs = len(list(path.glob("*.pdf")))
    xlsx = len(list(path.glob("*.xlsx"))) + len(list(path.glob("*.xls")))
    return {
        "exists": True,
        "path": str(path),
        "receipts": rc,
        "statements": pdfs,
        "invoices": xlsx,
        "file_count": len(shoebox_file_index(path)),
    }


@app.get("/api/analysis")
def get_analysis(
    shoebox: str | None = Query(None),
    force: bool = Query(False),
):
    path = _resolve_shoebox(shoebox)
    path.mkdir(parents=True, exist_ok=True)
    (path / "receipts").mkdir(exist_ok=True)
    try:
        result, chat_context, load_info = _load_analysis(path, force=force)
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if result.analytics is None:
        raise HTTPException(status_code=404, detail="No analytics available")
    sig = session.get("analysis_signature", "")
    return serialize_pipeline_result(
        result,
        chat_context=chat_context,
        signature=sig,
        load_meta=load_info,
    )


@app.post("/api/analysis/refresh")
def refresh_analysis(shoebox: str | None = Query(None)):
    path = _resolve_shoebox(shoebox)
    try:
        result, chat_context, load_info = _load_analysis(path, force=True)
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    sig = session.get("analysis_signature", "")
    return serialize_pipeline_result(
        result,
        chat_context=chat_context,
        signature=sig,
        load_meta=load_info,
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, shoebox: str | None = Query(None)):
    path = _resolve_shoebox(shoebox)
    context = session.get("chat_context")
    if not context:
        try:
            _, chat_context, _ = _load_analysis(path, force=False)
            context = chat_context
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
    reply = generate_reply(body.message, context, body.history)
    return ChatResponse(reply=reply)


@app.get("/api/receipts/{filename}")
def receipt_image(filename: str, shoebox: str | None = Query(None)):
    path = _resolve_shoebox(shoebox) / "receipts" / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Receipt image not found")
    return FileResponse(path)


@app.post("/api/upload/receipts")
async def upload_receipts(
    shoebox: str | None = Query(None),
    files: list[UploadFile] = File(...),
):
    path = _resolve_shoebox(shoebox)
    wrappers = []
    for f in files:
        data = await f.read()
        wrappers.append(_BytesFile(f.filename or "receipt.jpg", data))
    names = save_receipts(path, wrappers)
    clear_analysis_keys()
    return {"saved": names}


@app.post("/api/upload/statement")
async def upload_statement(
    shoebox: str | None = Query(None),
    file: UploadFile = File(...),
):
    path = _resolve_shoebox(shoebox)
    data = await file.read()
    name = save_statement(path, _BytesFile(file.filename or "statement.pdf", data))
    clear_analysis_keys()
    return {"saved": name}


@app.post("/api/upload/invoices")
async def upload_invoices(
    shoebox: str | None = Query(None),
    file: UploadFile = File(...),
):
    path = _resolve_shoebox(shoebox)
    data = await file.read()
    name = save_invoices(path, _BytesFile(file.filename or "invoices.xlsx", data))
    clear_analysis_keys()
    return {"saved": name}


@app.post("/api/upload/notes")
async def upload_notes(
    shoebox: str | None = Query(None),
    text: str = Form(""),
    file: UploadFile | None = File(None),
):
    path = _resolve_shoebox(shoebox)
    uploaded = None
    if file and file.filename:
        data = await file.read()
        uploaded = _BytesFile(file.filename, data)
    name = append_notes(path, text, uploaded)
    clear_analysis_keys()
    return {"saved": name}


@app.post("/api/export/pdf")
def export_pdf(shoebox: str | None = Query(None)):
    path = _resolve_shoebox(shoebox)
    result = session.get("pipeline_result")
    if result is None:
        result, _, _ = _load_analysis(path, force=False)
    pdf_path = build_pdf_report(result)
    if not pdf_path or not Path(pdf_path).is_file():
        raise HTTPException(status_code=400, detail="Could not generate PDF (fix validation issues first)")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=Path(pdf_path).name,
    )
