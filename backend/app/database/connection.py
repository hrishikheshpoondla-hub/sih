"""
backend/app/database/connection.py
DuckDB connection management for SIH26146.
Provides thread-safe connections, path resolution, and transaction helpers.
"""

import os
import duckdb
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "database" / "sih26146.duckdb"

class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            env_path = os.getenv("DUCKDB_PATH")
            self.db_path = Path(env_path) if env_path else DEFAULT_DB_PATH
        else:
            self.db_path = Path(db_path)
            
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = DatabaseManager(db_path)
        return cls._instance

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        # DuckDB in-process connection
        return duckdb.connect(str(self.db_path))

    def execute_script(self, sql_script: str):
        conn = self.get_connection()
        try:
            conn.execute(sql_script)
        finally:
            conn.close()

def get_db(db_path: Optional[Path] = None) -> duckdb.DuckDBPyConnection:
    manager = DatabaseManager.get_instance(db_path)
    return manager.get_connection()
