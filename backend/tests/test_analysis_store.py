from pathlib import Path

from src.cache.analysis_store import (
    diff_file_index,
    file_index_signature,
    shoebox_file_index,
)


def test_shoebox_file_index_empty_dir(tmp_path):
    assert shoebox_file_index(tmp_path) == {}


def test_file_index_signature_stable():
    index = {"receipts/a.png": {"mtime": 1.0, "size": 100}}
    assert file_index_signature(index) == file_index_signature(index.copy())


def test_diff_detects_added_changed_removed():
    old = {"a.pdf": {"mtime": 1.0, "size": 10}}
    new = {
        "a.pdf": {"mtime": 2.0, "size": 10},
        "b.pdf": {"mtime": 1.0, "size": 20},
    }
    diff = diff_file_index(old, new)
    assert diff.changed == ["a.pdf"]
    assert diff.added == ["b.pdf"]
    assert diff.removed == []
    assert diff.needs_work


def test_shoebox_file_index_finds_receipt(tmp_path):
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    img = receipts / "test.png"
    img.write_bytes(b"fake")
    index = shoebox_file_index(tmp_path)
    assert "receipts/test.png" in index
    assert index["receipts/test.png"]["size"] == len(b"fake")
