from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.supabase import get_supabase_admin_client

# FastAPI scheme that extracts "Authorization: Bearer <token>" headers.
# auto_error=False lets us return a clean 401 instead of the default 403.
_bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Minimal representation of a verified Supabase user.

    Populated exclusively from the decoded JWT — never from request body data.
    """

    def __init__(self, id: str, email: str):
        self.id = id
        self.email = email

    def __repr__(self) -> str:
        return f"AuthenticatedUser(id={self.id!r}, email={self.email!r})"


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthenticatedUser:
    """FastAPI dependency — verifies the Supabase JWT and returns the caller.

    Usage::

        @router.get("/protected")
        def protected(user: CurrentUser):
            return {"user_id": user.id}

    Raises:
        HTTPException 401 – token missing, malformed, expired, or rejected by Supabase.
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Reject missing or empty Authorization header immediately.
    if credentials is None or not credentials.credentials:
        raise _unauthorized

    token = credentials.credentials

    # 2. Verify via Supabase Admin API (get_user validates signature +
    #    expiry server-side — no JWT secret needed in the backend config).
    try:
        admin = get_supabase_admin_client()
        response = admin.auth.get_user(token)
        sb_user = response.user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if sb_user is None:
        raise _unauthorized

    # 3. Build AuthenticatedUser from the *verified* token payload only.
    #    User IDs supplied in request bodies must never be trusted.
    return AuthenticatedUser(id=str(sb_user.id), email=sb_user.email or "")


# Convenience type alias for route signatures.
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
