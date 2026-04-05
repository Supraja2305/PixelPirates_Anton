# main.py
# ============================================================
# Anton RX — Medical Benefit Drug Policy Tracker
# FastAPI Application Entry Point
#
# This file:
#   1. Creates the FastAPI app
#   2. Registers all middleware (CORS, rate limiting)
#   3. Registers all routers (API routes)
#   4. Registers error handlers
#   5. Adds health check endpoint
#
# Run with:
#   uvicorn main:app --reload --port 8000
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from config import get_settings
from utils.error_handler import register_exception_handlers
from utils.rate_limiter import create_limiter, rate_limit_exceeded_handler

# Import all routers
from api.auth_route import router as auth_router
from api.ingest import router as ingest_router
from api.drug import router as drug_router
from api.payer import router as payer_router
from api.compare import router as compare_router
from api.search import router as search_router
from api.changes import router as changes_router
from api.changes import alerts_router

settings = get_settings()

# ── Create app ────────────────────────────────────────────────
app = FastAPI(
    title="Anton RX — Medical Benefit Drug Policy Tracker",
    description=(
        "AI-powered system to ingest, parse, normalize, and compare "
        "medical benefit drug policies from multiple health plans."
    ),
    version="1.0.0",
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc UI
    debug=settings.debug,
)

# ── Rate Limiter ──────────────────────────────────────────────
limiter = create_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ── CORS Middleware ───────────────────────────────────────────
# Allow the React frontend to call this backend.
# In production, replace "*" with your actual frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Error Handlers ───────────────────────────────────
register_exception_handlers(app)

# ── Register All Routers ──────────────────────────────────────
app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(drug_router)
app.include_router(payer_router)
app.include_router(compare_router)
app.include_router(search_router)
app.include_router(changes_router)
app.include_router(alerts_router)


# ── Health Check ──────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint.
    Returns OK if the server is running.
    Used by deployment platforms (Render, Railway, etc.) to verify
    the service is alive.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "1.0.0",
    }


# ── Root endpoint ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    """API root — redirects to docs."""
    return {
        "message": "Anton RX Policy Tracker API",
        "docs": "/docs",
        "health": "/health",
    }


# ── Run directly (dev mode) ───────────────────────────────────
# In production, use: uvicorn main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)