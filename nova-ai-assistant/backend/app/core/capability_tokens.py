"""NOVA Scoped Capability Tokens Module.

Provides short-lived, cryptographically signed permission tokens for tool calls.
Each tool invocation must present a valid capability token scoped specifically to:
  1. The target tool name
  2. The allowed capability scopes (e.g., 'web_search:read', 'database:query')
  3. The calling user_id, task_id, and plan_id
  4. A short time-to-live expiration window (default 60 seconds)
"""
import os
import time
import uuid
import logging
from typing import List, Optional
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

# Secret key for HMAC-SHA256 signing of capability tokens
_CAPABILITY_SECRET = (
    settings.SUPABASE_SERVICE_ROLE_KEY
    or os.getenv("CAPABILITY_TOKEN_SECRET", "nova-default-capability-secret-key-32bytes")
)
_ALGORITHM = "HS256"
_DEFAULT_TTL_SECONDS = 60  # Short expiration window (60s)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class CapabilityTokenError(Exception):
    """Base exception for capability token failures."""
    pass


class ExpiredCapabilityTokenError(CapabilityTokenError):
    """Raised when a capability token has expired."""
    pass


class UnauthorizedCapabilityTokenError(CapabilityTokenError):
    """Raised when a capability token has invalid scope or tool mismatch."""
    pass


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CapabilityTokenPayload(BaseModel):
    jti: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    task_id: str
    plan_id: str
    tool_name: str
    allowed_scopes: List[str]
    iat: float = Field(default_factory=time.time)
    exp: float


# ---------------------------------------------------------------------------
# Token Creator & Verifier
# ---------------------------------------------------------------------------

def create_capability_token(
    user_id: str,
    task_id: str,
    plan_id: str,
    tool_name: str,
    allowed_scopes: List[str],
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> str:
    """Create a short-lived signed capability token for a specific tool call.

    Args:
        user_id: ID of the executing user.
        task_id: ID of the background task.
        plan_id: ID of the current plan.
        tool_name: Target tool name authorized for invocation.
        allowed_scopes: List of scope strings authorized (e.g. ['web_search:read']).
        ttl_seconds: Expiration window in seconds (default 60s).

    Returns:
        Encoded JWT capability token string.
    """
    now = time.time()
    payload = {
        "jti": str(uuid.uuid4()),
        "user_id": str(user_id),
        "task_id": str(task_id),
        "plan_id": str(plan_id),
        "tool_name": str(tool_name),
        "allowed_scopes": allowed_scopes,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    encoded = jwt.encode(payload, _CAPABILITY_SECRET, algorithm=_ALGORITHM)
    return encoded


def verify_capability_token(
    token: str,
    required_tool: str,
    required_scope: str,
    expected_user_id: Optional[str] = None,
) -> CapabilityTokenPayload:
    """Verify a capability token before tool execution.

    Args:
        token: The encoded capability token string.
        required_tool: The tool attempting execution.
        required_scope: The scope required for this action (e.g. 'web_search:read').
        expected_user_id: Optional expected user ID for user association check.

    Returns:
        Verified CapabilityTokenPayload object.

    Raises:
        ExpiredCapabilityTokenError: If current time exceeds token exp.
        UnauthorizedCapabilityTokenError: If tool name or required scope does not match.
        CapabilityTokenError: If signature is invalid or token is malformed.
    """
    if not token:
        raise UnauthorizedCapabilityTokenError("Capability token is missing.")

    try:
        data = jwt.decode(token, _CAPABILITY_SECRET, algorithms=[_ALGORITHM])
    except ExpiredSignatureError as e:
        raise ExpiredCapabilityTokenError(f"Capability token has expired: {str(e)}") from e
    except JWTError as e:
        raise CapabilityTokenError(f"Invalid capability token signature or format: {str(e)}") from e


    payload = CapabilityTokenPayload(**data)
    now = time.time()

    # 1. Check expiration
    if now > payload.exp:
        raise ExpiredCapabilityTokenError(
            f"Capability token expired {now - payload.exp:.1f}s ago."
        )

    # 2. Check target tool association
    if payload.tool_name != required_tool:
        raise UnauthorizedCapabilityTokenError(
            f"Token tool mismatch: authorized for '{payload.tool_name}', but attempted execution on '{required_tool}'."
        )

    # 3. Check required scope
    if required_scope not in payload.allowed_scopes:
        raise UnauthorizedCapabilityTokenError(
            f"Token scope unauthorized: required scope '{required_scope}' is missing from token allowed scopes {payload.allowed_scopes}."
        )

    # 4. Check user association if expected_user_id supplied
    if expected_user_id and payload.user_id != str(expected_user_id):
        raise UnauthorizedCapabilityTokenError(
            f"User mismatch: token issued for user '{payload.user_id}', but called by user '{expected_user_id}'."
        )

    return payload
