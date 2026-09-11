"""
scripts/run_ingest.py
CLI tool to ingest CSV, JSON, or XML datasets into the DuckDB database.
"""

import sys
import argparse
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.ingestion.pipeline import IngestionPipeline
from app.database.connection import DatabaseManager

def main():
    parser = argparse.ArgumentParser(description="Ingest Bitcoin metadata file into DuckDB")
    parser.add_argument("file_path", type=str, help="Path to CSV, JSON, or XML dataset")
    args = parser.parse_args()

    fp = Path(args.file_path)
    if not fp.exists():
        print(f"[ERROR] File not found: {fp}")
        sys.exit(1)

    print("=" * 70)
    print(f"SIH26146 Dataset Ingestion: {fp.name}")
    print("=" * 70)

    pipeline = IngestionPipeline()
    result = pipeline.ingest_file(fp)

    print(f"Batch ID:        {result['batch_id']}")
    print(f"Format:          {result['file_format']}")
    print(f"Total Records:   {result['total_records']}")
    print(f"Valid Records:   {result['valid_records']}")
    print(f"Invalid Records: {result['invalid_records']}")
    print(f"Status:          {result['status']}")

    # Print summary counts from DB
    conn = DatabaseManager.get_instance().get_connection()
    try:
        raw_cnt = conn.execute("SELECT count(*) FROM raw_records;").fetchone()[0]
        tx_cnt = conn.execute("SELECT count(*) FROM transactions;").fetchone()[0]
        in_cnt = conn.execute("SELECT count(*) FROM transaction_inputs;").fetchone()[0]
        out_cnt = conn.execute("SELECT count(*) FROM transaction_outputs;").fetchone()[0]
        net_cnt = conn.execute("SELECT count(*) FROM network_observations;").fetchone()[0]
        ent_cnt = conn.execute("SELECT count(*) FROM entities;").fetchone()[0]

        print("\nCurrent Database State:")
        print(f"  - raw_records:          {raw_cnt}")
        print(f"  - transactions:         {tx_cnt}")
        print(f"  - transaction_inputs:   {in_cnt}")
        print(f"  - transaction_outputs:  {out_cnt}")
        print(f"  - network_observations: {net_cnt}")
        print(f"  - entities (all types): {ent_cnt}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
