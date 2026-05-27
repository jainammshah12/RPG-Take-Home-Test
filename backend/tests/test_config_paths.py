from pathlib import Path

from src.config import REPO_ROOT, SHOEBOX_DIR


def test_shoebox_points_at_repo_root():
    assert SHOEBOX_DIR == REPO_ROOT / "shoebox"
    assert SHOEBOX_DIR.name == "shoebox"
    assert (REPO_ROOT / "backend").is_dir()
