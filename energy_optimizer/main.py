"""
Energy Optimizer Agent — Phase 1 (Local Deployment)
FastAPI + DuckDB | No Auth | Single Process

Contract: CON-004 | Domain: Energy & ESG
Tagline: Detects energy inefficiency by asset and links to equipment condition

Run with: python -m uvicorn energy_optimizer.main:app --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os

from .data.loader import load_all
from .data.db import reset_db, get_engine_info
from .agents.energy.routes import router as energy_router

# --- App Configuration ---
app = FastAPI(
    title="Energy Optimizer Agent",
    description=(
        "AI-powered energy intelligence for manufacturing. "
        "Real-time consumption monitoring, anomaly detection linked to equipment health, "
        "load dispatch optimization, and ESG/carbon tracking."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS (Phase 1: allow all for local dev) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Routers ---
app.include_router(energy_router)


# --- Startup Event ---
@app.on_event("startup")
def on_startup():
    """Load CSV data into DuckDB on startup."""
    reset_db()
    load_all()
    print("=" * 60)
    print("  Energy Optimizer Agent v1.0.0 — Phase 1 (Local)")
    print("  Contract: CON-004 | Domain: Energy & ESG")
    print(f"  DB Engine: {get_engine_info()}")
    print("  API Docs: http://localhost:8000/docs")
    print("=" * 60)


# --- Root Endpoint ---
@app.get("/", tags=["System"])
def root():
    """Platform root — serves frontend HTML if present, else API info."""
    html_path = os.path.join(
        os.path.dirname(__file__), "..", "manuai_unified_platform_v4.html"
    )
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return {
        "agent": "Energy Optimizer",
        "contract": "CON-004",
        "domain": "Energy & ESG",
        "version": "1.0.0",
        "phase": "Phase 1 — Local",
        "docs": "/docs",
        "endpoints": {
            "context": "/agents/energy/context?plant_key=us",
            "kpis": "/agents/energy/kpis",
            "anomalies": "/agents/energy/anomalies",
            "dispatch": "/agents/energy/dispatch",
            "attribution": "/agents/energy/attribution",
            "esg": "/agents/energy/esg",
            "forecast": "/agents/energy/forecast?period=24h",
            "insights": "/agents/energy/insights",
            "charts_consumers": "/agents/energy/charts/consumers",
            "charts_load_profile": "/agents/energy/charts/load-profile",
        },
    }


# --- Health Check (for future K8s readiness) ---
@app.get("/healthz", tags=["System"])
def health_check():
    """Liveness probe."""
    return {"status": "healthy", "agent": "energy_optimizer", "phase": "local"}


@app.get("/readyz", tags=["System"])
def readiness_check():
    """Readiness probe — checks DB is loaded."""
    from .data.db import query
    try:
        result = query("SELECT COUNT(*) as cnt FROM energy_assets")
        count = result[0]["cnt"] if result else 0
        if count > 0:
            return {"status": "ready", "tables_loaded": True, "energy_assets": count}
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "tables_loaded": False},
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(e)},
        )


@app.post("/reload", tags=["System"])
def reload_data():
    """Reload all CSV data into DuckDB (dev utility)."""
    reset_db()
    load_all()
    return {"status": "reloaded", "message": "All CSV data reloaded into DuckDB"}
