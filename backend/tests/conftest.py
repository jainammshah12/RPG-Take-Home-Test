"""Shared pytest fixtures — paths resolve to repo-root shoebox/."""

from pathlib import Path

import pytest

from src.config import SHOEBOX_DIR


@pytest.fixture(scope="session")
def shoebox_dir() -> Path:
    """Absolute path to the project shoebox (not backend/shoebox)."""
    if not SHOEBOX_DIR.is_dir():
        pytest.skip(f"Shoebox not found at {SHOEBOX_DIR}")
    return SHOEBOX_DIR
