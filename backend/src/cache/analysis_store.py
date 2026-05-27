"""Disk-backed analysis cache with incremental parsing for new/changed shoebox files."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.analytics.metrics import compute_analytics
from src.cleaning.normalizer import combine_sources
from src.config import ANALYSIS_CACHE_DIR
from src.enrichment.categorizer import assign_categories
from src.ingestion.loader import (
    INVOICE_EXTENSIONS,
    NOTES_EXTENSIONS,
    RECEIPT_EXTENSIONS,
    STATEMENT_EXTENSIONS,
    IngestedFiles,
    ingest,
)
from src.parsing.invoice_parser import parse_all_invoices
from src.parsing.notes_parser import parse_all_notes
from src.parsing.receipt_ocr import parse_receipts
from src.parsing.statement_parser import parse_statements
from src.pipeline import PipelineResult
from src.ui.chat_assistant import build_dashboard_context
from src.validation.validator import validate

_PARSED_KEYS = ("receipts", "statement", "invoices", "notes")


@dataclass
class FileDiff:
    added: list[str]
    changed: list[str]
    removed: list[str]

    @property
    def needs_work(self) -> bool:
        return bool(self.added or self.changed or self.removed)


def shoebox_file_index(shoebox_dir: Path) -> dict[str, dict[str, float | int]]:
    """Map relative shoebox paths to mtime/size metadata."""
    base = shoebox_dir.resolve()
    if not base.is_dir():
        return {}

    index: dict[str, dict[str, float | int]] = {}

    receipts_dir = base / "receipts"
    if receipts_dir.is_dir():
        for path in receipts_dir.iterdir():
            if path.is_file() and path.suffix.lower() in RECEIPT_EXTENSIONS:
                rel = path.relative_to(base).as_posix()
                st = path.stat()
                index[rel] = {"mtime": st.st_mtime, "size": st.st_size}

    for path in base.iterdir():
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in STATEMENT_EXTENSIONS or suffix in INVOICE_EXTENSIONS or suffix in NOTES_EXTENSIONS:
            rel = path.relative_to(base).as_posix()
            st = path.stat()
            index[rel] = {"mtime": st.st_mtime, "size": st.st_size}

    return dict(sorted(index.items()))


def file_index_signature(index: dict[str, dict]) -> str:
    payload = json.dumps(index, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def diff_file_index(
    stored: dict[str, dict],
    current: dict[str, dict],
) -> FileDiff:
    added: list[str] = []
    changed: list[str] = []
    removed: list[str] = []

    for rel, meta in current.items():
        if rel not in stored:
            added.append(rel)
        elif stored[rel] != meta:
            changed.append(rel)

    for rel in stored:
        if rel not in current:
            removed.append(rel)

    return FileDiff(added=added, changed=changed, removed=removed)


def _cache_dir(shoebox_dir: Path) -> Path:
    key = hashlib.sha256(str(shoebox_dir.resolve()).encode()).hexdigest()[:16]
    return ANALYSIS_CACHE_DIR / key


def _manifest_path(cache_dir: Path) -> Path:
    return cache_dir / "manifest.json"


def _parsed_dir(cache_dir: Path) -> Path:
    return cache_dir / "parsed"


def _load_manifest(cache_dir: Path) -> dict:
    path = _manifest_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_manifest(cache_dir: Path, shoebox_dir: Path, file_index: dict[str, dict]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "shoebox": str(shoebox_dir.resolve()),
        "files": file_index,
        "signature": file_index_signature(file_index),
    }
    _manifest_path(cache_dir).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _empty_parsed() -> dict[str, pd.DataFrame]:
    return {key: pd.DataFrame() for key in _PARSED_KEYS}


def _load_parsed(cache_dir: Path) -> dict[str, pd.DataFrame]:
    parsed_dir = _parsed_dir(cache_dir)
    out = _empty_parsed()
    if not parsed_dir.is_dir():
        return out
    for key in _PARSED_KEYS:
        path = parsed_dir / f"{key}.parquet"
        if path.is_file():
            out[key] = pd.read_parquet(path)
    return out


def _save_parsed(cache_dir: Path, parsed: dict[str, pd.DataFrame]) -> None:
    parsed_dir = _parsed_dir(cache_dir)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    for key in _PARSED_KEYS:
        df = parsed.get(key, pd.DataFrame())
        path = parsed_dir / f"{key}.parquet"
        if df is not None and not df.empty:
            df.to_parquet(path, index=False)
        elif path.is_file():
            path.unlink()


def _save_chat_context(cache_dir: Path, context: str) -> None:
    (cache_dir / "chat_context.txt").write_text(context, encoding="utf-8")


def _load_chat_context(cache_dir: Path) -> str | None:
    path = cache_dir / "chat_context.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def _file_kind(rel: str) -> str | None:
    if rel.startswith("receipts/"):
        return "receipts"
    lower = rel.lower()
    if lower.endswith(".pdf"):
        return "statement"
    if lower.endswith(INVOICE_EXTENSIONS):
        return "invoices"
    if lower.endswith(NOTES_EXTENSIONS):
        return "notes"
    return None


def _resolve_paths(shoebox_dir: Path, rel_paths: list[str]) -> list[Path]:
    return [shoebox_dir / rel for rel in rel_paths]


def _merge_by_source_file(
    existing: pd.DataFrame,
    new_rows: pd.DataFrame,
    removed_files: set[str],
    replaced_files: set[str],
) -> pd.DataFrame:
    if existing is None or existing.empty:
        base = pd.DataFrame()
    else:
        if "source_file" not in existing.columns:
            base = existing.copy()
        else:
            drop_names = removed_files | replaced_files
            base = existing[~existing["source_file"].astype(str).isin(drop_names)].copy()

    if new_rows is not None and not new_rows.empty:
        base = pd.concat([base, new_rows], ignore_index=True)
    return base


def _parse_paths(kind: str, paths: list[Path]) -> pd.DataFrame:
    if not paths:
        return pd.DataFrame()
    if kind == "receipts":
        return parse_receipts(paths)
    if kind == "statement":
        return parse_statements(paths)
    if kind == "invoices":
        return parse_all_invoices(paths)
    if kind == "notes":
        return parse_all_notes(paths)
    return pd.DataFrame()


def _apply_incremental_parse(
    shoebox_dir: Path,
    parsed: dict[str, pd.DataFrame],
    diff: FileDiff,
) -> dict[str, pd.DataFrame]:
    """Parse only added/changed files and merge into cached parsed frames."""
    to_process = diff.added + diff.changed
    removed_set = set(diff.removed)
    replaced_set = set(diff.changed)

    by_kind: dict[str, list[str]] = {k: [] for k in _PARSED_KEYS}
    for rel in to_process:
        kind = _file_kind(rel)
        if kind:
            by_kind[kind].append(rel)

    out = {k: parsed.get(k, pd.DataFrame()).copy() for k in _PARSED_KEYS}

    for kind in _PARSED_KEYS:
        rels = by_kind[kind]
        if not rels and not (removed_set or replaced_set):
            continue
        paths = _resolve_paths(shoebox_dir, rels)
        new_rows = _parse_paths(kind, paths)
        out[kind] = _merge_by_source_file(
            out[kind],
            new_rows,
            removed_files={r for r in removed_set if _file_kind(r) == kind},
            replaced_files={r for r in replaced_set if _file_kind(r) == kind},
        )

    # Drop rows for removed files even when nothing new was parsed
    for kind in _PARSED_KEYS:
        df = out[kind]
        if df.empty or "source_file" not in df.columns:
            continue
        removed_for_kind = {r for r in removed_set if _file_kind(r) == kind}
        if removed_for_kind:
            out[kind] = df[~df["source_file"].astype(str).isin(removed_for_kind)].copy()

    return out


def _finalize_result(ingested: IngestedFiles, parsed: dict[str, pd.DataFrame]) -> PipelineResult:
    result = PipelineResult(ingested=ingested, parsed=parsed)
    result.transactions = assign_categories(combine_sources(parsed))
    result.validation = validate(result.transactions)
    result.analytics = compute_analytics(result.transactions, parsed)
    return result


def invalidate_analysis_cache(shoebox_dir: Path) -> None:
    cache_dir = _cache_dir(shoebox_dir)
    if cache_dir.is_dir():
        shutil.rmtree(cache_dir, ignore_errors=True)


@dataclass
class AnalysisLoadResult:
    result: PipelineResult
    chat_context: str
    signature: str
    parsed_new_files: int = 0
    from_disk: bool = False


def load_analysis(
    shoebox_dir: Path,
    *,
    force: bool = False,
) -> AnalysisLoadResult:
    """
    Load analysis from disk cache, parsing only new or changed shoebox files.
    """
    shoebox_dir = shoebox_dir.resolve()
    ingested = ingest(shoebox_dir)
    file_index = shoebox_file_index(shoebox_dir)
    signature = file_index_signature(file_index)
    cache_dir = _cache_dir(shoebox_dir)

    if force:
        invalidate_analysis_cache(shoebox_dir)
        cache_dir = _cache_dir(shoebox_dir)

    manifest = _load_manifest(cache_dir)
    stored_files = manifest.get("files", {}) if manifest else {}
    diff = diff_file_index(stored_files, file_index)

    if not force and not diff.needs_work and manifest.get("signature") == signature:
        parsed = _load_parsed(cache_dir)
        if any(not df.empty for df in parsed.values()) or not file_index:
            result = _finalize_result(ingested, parsed)
            context = _load_chat_context(cache_dir) or build_dashboard_context(result)
            return AnalysisLoadResult(
                result=result,
                chat_context=context,
                signature=signature,
                from_disk=True,
            )

    parsed = _empty_parsed() if force or not stored_files else _load_parsed(cache_dir)

    if not file_index:
        result = _finalize_result(ingested, parsed)
        context = build_dashboard_context(result)
        _save_parsed(cache_dir, parsed)
        _save_manifest(cache_dir, shoebox_dir, file_index)
        _save_chat_context(cache_dir, context)
        return AnalysisLoadResult(
            result=result,
            chat_context=context,
            signature=signature,
            parsed_new_files=0,
        )

    # Full parse when no cache yet; incremental when we have stored state
    if force or not stored_files:
        from src.parsing import parse_all

        parsed = parse_all(ingested)
        new_count = len(file_index)
    else:
        parsed = _apply_incremental_parse(shoebox_dir, parsed, diff)
        new_count = len(diff.added) + len(diff.changed)

    result = _finalize_result(ingested, parsed)
    context = build_dashboard_context(result)
    _save_parsed(cache_dir, parsed)
    _save_manifest(cache_dir, shoebox_dir, file_index)
    _save_chat_context(cache_dir, context)

    return AnalysisLoadResult(
        result=result,
        chat_context=context,
        signature=signature,
        parsed_new_files=new_count,
        from_disk=False,
    )


def analysis_needs_loading(
    shoebox_dir: Path,
    session_state,
    *,
    force: bool = False,
) -> bool:
    """True when we must read disk or parse files (not a warm session hit)."""
    if force:
        return True
    file_index = shoebox_file_index(shoebox_dir)
    signature = file_index_signature(file_index)
    if (
        session_state.get("analysis_signature") == signature
        and session_state.get("pipeline_result") is not None
        and session_state.get("chat_context")
        and not _session_needs_refresh(shoebox_dir, signature)
    ):
        return False
    cache_dir = _cache_dir(shoebox_dir)
    manifest = _load_manifest(cache_dir)
    stored = manifest.get("files", {}) if manifest else {}
    diff = diff_file_index(stored, file_index)
    if manifest.get("signature") == signature and not diff.needs_work:
        return False
    return True


def get_analysis_result(
    shoebox_dir: Path,
    session_state,
    *,
    force: bool = False,
) -> tuple[PipelineResult, str, AnalysisLoadResult]:
    """
    Return pipeline result + chat context, using session_state when valid
    and disk cache across browser refreshes.
    """
    file_index = shoebox_file_index(shoebox_dir)
    signature = file_index_signature(file_index)

    if not force:
        cached_sig = session_state.get("analysis_signature")
        cached_result = session_state.get("pipeline_result")
        cached_context = session_state.get("chat_context")
        if (
            cached_sig == signature
            and cached_result is not None
            and cached_context
            and not _session_needs_refresh(shoebox_dir, signature)
        ):
            return cached_result, cached_context, AnalysisLoadResult(
                result=cached_result,
                chat_context=cached_context,
                signature=signature,
                from_disk=True,
            )

    load = load_analysis(shoebox_dir, force=force)
    session_state["pipeline_result"] = load.result
    session_state["chat_context"] = load.chat_context
    session_state["analysis_signature"] = load.signature
    return load.result, load.chat_context, load


def _session_needs_refresh(shoebox_dir: Path, signature: str) -> bool:
    """True when disk manifest differs from current shoebox (new files since session hydrate)."""
    cache_dir = _cache_dir(shoebox_dir)
    manifest = _load_manifest(cache_dir)
    if not manifest:
        return True
    if manifest.get("signature") != signature:
        return True
    stored = manifest.get("files", {})
    current = shoebox_file_index(shoebox_dir)
    return diff_file_index(stored, current).needs_work
