"""Tasks router — stub.

Future: Celery task queue integration, task status polling.
"""

from fastapi import APIRouter
from app.core.security import CurrentUser

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/")
def tasks_health() -> dict:
    """Tasks service health check (unauthenticated)."""
    return {"service": "tasks", "status": "ready"}


@router.get("/my")
def list_my_tasks(user: CurrentUser) -> dict:
    """(Stub) List tasks belonging to the authenticated user."""
    return {
        "user_id": user.id,
        "tasks": [],
        "note": "stub — Celery/Supabase integration not yet implemented",
    }


@router.get("/{task_id}")
def get_task(task_id: str, user: CurrentUser) -> dict:
    """(Stub) Get status of a specific task."""
    return {
        "task_id": task_id,
        "user_id": user.id,
        "status": "stub — task lookup not yet implemented",
    }
