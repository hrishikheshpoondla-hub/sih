"""
backend/app/main.py
SIH26146 - Application Entry Point
FastAPI application with CORS, API routers, and health monitoring.
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import router as api_router
from app.database.connection import DatabaseManager
from app.database.schema import init_schema

app = FastAPI(
    title="SIH26146 - Bitcoin Traffic Monitoring & Analysis (NTRO)",
    description="Offline-capable AI/ML anomaly detection, clustering, and explainable investigation platform for Bitcoin transaction and network metadata.",
    version="1.0.0"
)

# CORS Middleware (Local offline dashboard access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event: Ensure database schema is ready
@app.on_event("startup")
def startup_event():
    db_mgr = DatabaseManager.get_instance()
    conn = db_mgr.get_connection()
    try:
        init_schema(conn)
    finally:
        conn.close()

from fastapi.responses import FileResponse

# Include API Router
app.include_router(api_router, prefix="/api")

@app.get("/api/info")
def project_info():
    return {
        "project": "SIH26146",
        "organization": "National Technical Research Organisation (NTRO)",
        "status": "ONLINE",
        "docs": "/docs",
        "api": "/api"
    }

# Mount static frontend build if it exists (for offline standalone delivery)
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static_assets")

    @app.get("/")
    def serve_index():
        return FileResponse(str(frontend_dist / "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    def root_fallback():
        return {
            "project": "SIH26146",
            "organization": "National Technical Research Organisation (NTRO)",
            "status": "ONLINE",
            "docs": "/docs",
            "api": "/api",
            "message": "Frontend not built yet. Run 'npm run build' in frontend/ directory."
        }
