import pytest
from pathlib import Path
from app.ingestion.pipeline import IngestionPipeline
from app.database.connection import DatabaseManager
from app.database.schema import init_schema, reset_schema

@pytest.fixture(scope="module")
def setup_db():
    conn = DatabaseManager.get_instance().get_connection()
    reset_schema(conn)
    conn.close()

def test_csv_ingestion(setup_db):
    sample_csv = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "synthetic_demo.csv"
    if sample_csv.exists():
        pipeline = IngestionPipeline()
        res = pipeline.ingest_file(sample_csv)
        assert res["status"] == "COMPLETED"
        assert res["valid_records"] > 0

def test_json_ingestion(setup_db):
    sample_json = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "synthetic_demo.json"
    if sample_json.exists():
        pipeline = IngestionPipeline()
        res = pipeline.ingest_file(sample_json)
        assert res["status"] == "COMPLETED"
        assert res["valid_records"] > 0
