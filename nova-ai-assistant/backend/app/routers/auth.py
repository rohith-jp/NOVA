"""Auth router — protected test endpoints.

These routes exist purely to verify that JWT authentication works end-to-end.
No agent functionality is implemented here.
"""
from fastapi import APIRouter

from app.core.security import CurrentUser

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
def get_me(user: CurrentUser) -> dict:
    """Protected endpoint.

    Returns the authenticated user's profile extracted from the verified JWT.
    The user ID is sourced *only* from the token — never from request body data.

    Responses:
        200 – valid token → user profile dict
        401 – missing or invalid token → ``{"detail": "Not authenticated"}``
    """
    return {
        "user_id": user.id,
        "email": user.email,
        "message": "JWT verified successfully",
    }
