"""Commands router — stub.

Future: Claude-powered natural language command dispatch.
"""
from fastapi import APIRouter
from app.core.security import CurrentUser

router = APIRouter(prefix="/api/commands", tags=["commands"])


@router.get("/")
def commands_health() -> dict:
    """Commands service health check (unauthenticated)."""
    return {"service": "commands", "status": "ready"}


@router.post("/run")
def run_command(user: CurrentUser, body: dict) -> dict:
    """(Stub) Submit a natural-language command.

    Future implementation will dispatch to Claude and return a task ID.
    """
    return {
        "user_id": user.id,
        "status": "stub — Claude integration not yet implemented",
        "received": body,
    }
