"""
scripts/init_database.py
Initializes the DuckDB analytical database for SIH26146.
Creates sequences, tables, and indexes, verifying all 14 required tables.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database.connection import DatabaseManager
from app.database.schema import init_schema, reset_schema

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Initialize DuckDB database for SIH26146")
    parser.add_argument("--reset", action="store_true", help="Reset schema if already present")
    args = parser.parse_args()

    db_mgr = DatabaseManager.get_instance()
    db_file = db_mgr.db_path
    print("=" * 70)
    print("SIH26146 DuckDB Database Initialization")
    print(f"Target Database File: {db_file}")
    print("=" * 70)

    conn = db_mgr.get_connection()
    try:
        if args.reset:
            print("[INFO] Resetting existing schema...")
            reset_schema(conn)
        else:
            print("[INFO] Initializing tables and sequences...")
            init_schema(conn)

        # Verification of tables
        tables_res = conn.execute("SHOW TABLES;").fetchall()
        table_names = [t[0] for t in tables_res]

        expected_tables = [
            "raw_records", "ingestion_batches", "transactions",
            "transaction_inputs", "transaction_outputs", "wallets",
            "network_observations", "ip_addresses", "entities",
            "entity_relationships", "entity_features", "anomaly_scores",
            "alert_evidence", "investigation_alerts"
        ]

        print(f"\nDetected Tables in Database ({len(table_names)}):")
        all_passed = True
        for expected in expected_tables:
            if expected in table_names:
                count = conn.execute(f"SELECT count(*) FROM {expected};").fetchone()[0]
                print(f"  [OK] Table '{expected:<24}' | Current Row Count: {count}")
            else:
                print(f"  [FAILED] Table '{expected:<24}' is MISSING!")
                all_passed = False

        if all_passed:
            print("\n[SUCCESS] All 14 required tables and sequences initialized successfully.")
        else:
            print("\n[ERROR] Schema initialization incomplete.")
            sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
