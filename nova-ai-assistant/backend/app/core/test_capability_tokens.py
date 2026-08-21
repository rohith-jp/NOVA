import time
from app.core.capability_tokens import (
    create_capability_token,
    verify_capability_token,
    ExpiredCapabilityTokenError,
    UnauthorizedCapabilityTokenError,
    CapabilityTokenError,
)


def test_valid_capability_token():
    print("\n=== TEST 1: Valid Capability Token ===")
    token = create_capability_token(
        user_id="usr_12345",
        task_id="task_9988",
        plan_id="plan_7766",
        tool_name="web_search",
        allowed_scopes=["web_search:read"],
        ttl_seconds=60,
    )
    print(f"Generated token (len={len(token)}): {token[:40]}...")

    payload = verify_capability_token(
        token=token,
        required_tool="web_search",
        required_scope="web_search:read",
        expected_user_id="usr_12345",
    )
    print(f"[OK] Token verified successfully! User: {payload.user_id}, Tool: {payload.tool_name}, Scopes: {payload.allowed_scopes}")
    assert payload.user_id == "usr_12345"
    assert payload.tool_name == "web_search"
    assert "web_search:read" in payload.allowed_scopes


def test_expired_capability_token():
    print("\n=== TEST 2: Expired Capability Token ===")
    # Create token with ttl_seconds=-1 (already expired)
    token = create_capability_token(
        user_id="usr_12345",
        task_id="task_9988",
        plan_id="plan_7766",
        tool_name="web_search",
        allowed_scopes=["web_search:read"],
        ttl_seconds=-1,
    )

    try:
        verify_capability_token(
            token=token,
            required_tool="web_search",
            required_scope="web_search:read",
        )
        assert False, "Expected ExpiredCapabilityTokenError was NOT raised!"
    except ExpiredCapabilityTokenError as e:
        print(f"[OK] Caught ExpiredCapabilityTokenError as expected: '{e}'")


def test_unauthorized_scope():
    print("\n=== TEST 3: Unauthorized Scope ===")
    # Token only grants 'web_search:read'
    token = create_capability_token(
        user_id="usr_12345",
        task_id="task_9988",
        plan_id="plan_7766",
        tool_name="web_search",
        allowed_scopes=["web_search:read"],
        ttl_seconds=60,
    )

    try:
        # Attempt to require 'database:query' scope
        verify_capability_token(
            token=token,
            required_tool="web_search",
            required_scope="database:query",
        )
        assert False, "Expected UnauthorizedCapabilityTokenError was NOT raised!"
    except UnauthorizedCapabilityTokenError as e:
        print(f"[OK] Caught UnauthorizedCapabilityTokenError as expected: '{e}'")


def test_mismatched_tool():
    print("\n=== TEST 4: Mismatched Target Tool ===")
    # Token created for 'web_search'
    token = create_capability_token(
        user_id="usr_12345",
        task_id="task_9988",
        plan_id="plan_7766",
        tool_name="web_search",
        allowed_scopes=["web_search:read"],
        ttl_seconds=60,
    )

    try:
        # Attempt to use token for 'email_notification_tool'
        verify_capability_token(
            token=token,
            required_tool="email_notification_tool",
            required_scope="web_search:read",
        )
        assert False, "Expected UnauthorizedCapabilityTokenError was NOT raised!"
    except UnauthorizedCapabilityTokenError as e:
        print(f"[OK] Caught UnauthorizedCapabilityTokenError as expected: '{e}'")


def main():
    test_valid_capability_token()
    test_expired_capability_token()
    test_unauthorized_scope()
    test_mismatched_tool()
    print("\n==========================================")
    print(" ALL CAPABILITY TOKEN TESTS PASSED SUCCESSFULLY! ")
    print("==========================================")


if __name__ == "__main__":
    main()
