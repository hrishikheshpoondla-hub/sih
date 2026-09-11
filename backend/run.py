"""
backend/run.py
Server launcher script for SIH26146 backend.
Runs FastAPI on Uvicorn.
"""

import os
import sys
from pathlib import Path
import uvicorn

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def main():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    print("=" * 70)
    print("SIH26146 FastAPI Server")
    print(f"URL: http://{host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    print("=" * 70)

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    main()
