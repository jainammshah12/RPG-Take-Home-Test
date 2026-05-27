from fastapi.testclient import TestClient

from src.api.main import app
from src.config import SHOEBOX_DIR


client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_config_points_to_repo_shoebox():
    r = client.get("/api/config")
    assert r.status_code == 200
    path = r.json()["default_shoebox"]
    assert path.replace("\\", "/").endswith("/shoebox")
    assert SHOEBOX_DIR.resolve().as_posix() in path.replace("\\", "/")


def test_analysis_returns_data_from_repo_shoebox():
    r = client.get("/api/analysis", params={"shoebox": str(SHOEBOX_DIR)})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "analytics" in data
    assert "transactions" in data
    assert len(data["transactions"]) > 0
    assert data["analytics"]["revenue"] >= 0
