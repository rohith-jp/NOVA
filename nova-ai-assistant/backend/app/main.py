"""NOVA AI Assistant — FastAPI application entry point.

Start with:
    uvicorn app.main:app --reload
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.db.supabase import check_supabase_connection
from app.routers import auth, commands, demo, memory, security, tasks, voice, ws

load_dotenv()

# ---------------------------------------------------------------------------
# Allowed Origins for CORS
# ---------------------------------------------------------------------------
_ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks; yield for request handling; clean up on shutdown."""
    db_ok = check_supabase_connection()
    print(f"[NOVA] Supabase connection: {'OK' if db_ok else 'FAILED'}")
    print(f"[NOVA] CORS allowed origins: {_ALLOWED_ORIGINS}")
    print("[NOVA] Application ready.")
    yield
    print("[NOVA] Application shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NOVA AI Assistant API",
    description=(
        "Backend API for the NOVA AI Assistant. "
        "Provides authenticated routes for commands, tasks, memory, and real-time WebSocket communication."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware (order matters — outermost wraps first)
# ---------------------------------------------------------------------------
# 1. CORS — must be first so pre-flight OPTIONS requests are handled before auth.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Rate limiting — applied before logging so rejected requests are still logged.
app.add_middleware(RateLimitMiddleware)

# 3. Request logging — innermost, sees the final status code.
app.add_middleware(RequestLoggingMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)  # /api/auth
app.include_router(commands.router)  # /api/commands
app.include_router(tasks.router)  # /api/tasks
app.include_router(memory.router)  # /api/memory
app.include_router(security.router)  # /api/security
app.include_router(voice.router)  # /api/voice
app.include_router(ws.router)  # /ws
app.include_router(demo.router)  # /api/demo  (DEMO_MODE=true only)


# ---------------------------------------------------------------------------
# Root & Health Endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["system"])
def read_root() -> dict:
    """API root — confirms the service is running."""
    return {"message": "NOVA AI Assistant API is running", "version": "0.1.0"}


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Health check — includes live Supabase connectivity status."""
    db_connected = check_supabase_connection()
    return {
        "status": "ok",
        "service": "nova-backend",
        "database": "connected" if db_connected else "disconnected",
    }
