"""Memory router — provides endpoints to list, search, and store semantic vector memories."""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.security import CurrentUser
from app.services import memory as memory_service

router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "general"
    source: str = "user_input"


@router.get("/")
def get_user_memories(user: CurrentUser) -> List[Dict[str, Any]]:
    """List all stored memories for the authenticated user (decrypted)."""
    return memory_service.list_memories(user.id)


@router.get("/search")
def search_user_memories(
    user: CurrentUser,
    q: str = Query(..., description="Query string to search memories"),
    limit: int = Query(5, ge=1, le=20),
) -> List[Dict[str, Any]]:
    """Semantic vector search for the authenticated user's memories."""
    try:
        results = memory_service.search_memory(
            user_id=user.id,
            query=q,
            match_count=limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store")
def store_user_memory(user: CurrentUser, body: MemoryStoreRequest) -> Dict[str, Any]:
    """Create and store a memory vector for the authenticated user."""
    try:
        payload = memory_service.create_memory(
            user_id=user.id,
            content=body.content,
            memory_type=body.memory_type,
            source=body.source
        )
        memory_id = memory_service.store_memory(payload)
        return {
            "status": "success",
            "id": memory_id,
            "memory_type": body.memory_type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
