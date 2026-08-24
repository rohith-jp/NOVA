"""
JWT Authentication Verification Script
Tests three scenarios against /api/auth/me:
  1. Valid Supabase JWT       → 200 + user profile
  2. Missing Authorization    → 401 Not authenticated
  3. Invalid / tampered token → 401 Token verification failed

Uses admin API to create and delete a temporary test user.
"""

import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

TEST_EMAIL = "nova_jwt_test@nova-internal.ai"
TEST_PASSWORD = "JwtTest2024!"

_user_id: str | None = None
_token: str | None = None

# ── Setup ──────────────────────────────────────────────────────────────────
print("=== SETUP: create confirmed test user ===")
try:
    res = admin.auth.admin.create_user(
        {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "email_confirm": True,
        }
    )
    _user_id = res.user.id
    print(f"[OK] User created: {_user_id}")
except Exception as e:
    if "already" in str(e).lower():
        print("[INFO] User already exists")
    else:
        raise

# Sign in to obtain a live JWT
res2 = anon.auth.sign_in_with_password({"email": TEST_EMAIL, "password": TEST_PASSWORD})
_token = res2.session.access_token
_user_id = str(res2.user.id)
print(f"[OK] Signed in, token length={len(_token)}")
print()

# ── Run FastAPI TestClient tests ───────────────────────────────────────────
from app.main import app  # noqa: E402 — import after env is loaded

client = TestClient(app, raise_server_exceptions=False)

# ── Test 1: Valid token ────────────────────────────────────────────────────
print("=== TEST 1: Valid JWT -> 200 ===")
r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {_token}"})
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
body = r.json()
assert body["user_id"] == _user_id, f"user_id mismatch: {body}"
assert body["email"] == TEST_EMAIL
assert "JWT verified successfully" in body["message"]
print(f"[OK] 200 user_id={body['user_id']}  email={body['email']}")
print()

# ── Test 2: Missing token ──────────────────────────────────────────────────
print("=== TEST 2: Missing token -> 401 ===")
r2 = client.get("/api/auth/me")
assert r2.status_code == 401, f"Expected 401, got {r2.status_code}: {r2.text}"
print(f"[OK] 401  detail={r2.json()['detail']}")
print()

# ── Test 3: Invalid token ──────────────────────────────────────────────────
print("=== TEST 3: Tampered token -> 401 ===")
bad_token = _token[:-10] + "XXXXXXXXXX"  # corrupt the signature
r3 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
assert r3.status_code == 401, f"Expected 401, got {r3.status_code}: {r3.text}"
print(f"[OK] 401  detail={r3.json()['detail']}")
print()

# ── Cleanup ────────────────────────────────────────────────────────────────
print("=== CLEANUP: delete test user ===")
try:
    admin.auth.admin.delete_user(_user_id)
    print(f"[OK] Test user deleted: {_user_id}")
except Exception as e:
    print(f"[INFO] Cleanup skipped: {e}")

print()
print("=== ALL JWT AUTH TESTS PASSED ===")
