import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

def test_statistics():
    res = client.get("/api/statistics")
    assert res.status_code == 200
    data = res.json()
    assert "total_transactions" in data
    assert "total_wallets" in data

def test_alerts_and_explanation():
    res = client.get("/api/alerts")
    assert res.status_code == 200
    alerts = res.json()
    if alerts:
        aid = alerts[0]["alert_id"]
        res_d = client.get(f"/api/alerts/{aid}")
        assert res_d.status_code == 200

        res_exp = client.post(f"/api/explain/{aid}")
        assert res_exp.status_code == 200
        assert "ai_explanation" in res_exp.json()

def test_upload_replace_mode():
    from pathlib import Path
    test_csv = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "SIH26146_test_transactions.csv"
    if not test_csv.exists():
        pytest.skip("Test CSV not found")

    with open(test_csv, "rb") as f:
        res = client.post(
            "/api/ingest",
            files={"file": ("SIH26146_test_transactions.csv", f, "text/csv")},
            data={"mode": "REPLACE", "dataset_id": "USER_UPLOAD"}
        )
    assert res.status_code == 200
    data = res.json()
    assert data["valid_records"] == 500
    assert data["mode"] == "REPLACE"
    assert data["transactions_inserted"] == 500
    assert data["wallets_count"] > 0
    assert data["total_alerts"] > 0
    assert "ml_results" in data

    # Verify overview statistics return only the uploaded dataset
    stats_res = client.get("/api/statistics")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_transactions"] == 500

