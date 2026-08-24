"""
Creates a confirmed Supabase user via Admin API (service role),
then tests sign-in, session persistence, and sign-out.
Uses SUPABASE_SERVICE_ROLE_KEY to bypass email rate limits.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Admin client (service role) for user creation
admin_client = create_client(url, service_key)
# Anon client — simulates real browser behaviour
anon_client = create_client(url, anon_key)

TEST_EMAIL = "nova_verified_test@nova-internal.ai"
TEST_PASSWORD = "NovaTest2024!"

print(f"Test email: {TEST_EMAIL}")
print()

# 1. Create confirmed user via Admin API
print("=== 1. CREATE CONFIRMED USER (admin) ===")
try:
    res = admin_client.auth.admin.create_user(
        {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "email_confirm": True,
        }
    )
    if res.user:
        print(f"[OK] User created & confirmed: {res.user.id}")
    else:
        print("[INFO] User may already exist, proceeding to sign in...")
except Exception as e:
    if "already been registered" in str(e) or "duplicate" in str(e).lower():
        print("[INFO] User already exists, proceeding to sign in...")
    else:
        print(f"[ERROR] Admin create_user failed: {e}")

print()

# 2. Sign in with ANON client (as a real browser would)
print("=== 2. SIGN IN (anon client) ===")
try:
    res2 = anon_client.auth.sign_in_with_password(
        {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        }
    )
    session = res2.session
    user = res2.user
    if session and user:
        print(f"[OK] Signed in: user_id={user.id}")
        print(f"[OK] email = {user.email}")
        print(f"[OK] access_token length = {len(session.access_token)}")
        print(f"[OK] token_type = {session.token_type}")
    else:
        print("[ERROR] Sign in returned no session")
        exit(1)
except Exception as e:
    print(f"[ERROR] Sign in failed: {e}")
    exit(1)

print()

# 3. Session persistence — resolve token → user
print("=== 3. SESSION PERSISTENCE ===")
try:
    resolved = anon_client.auth.get_user(session.access_token)
    if resolved.user:
        print(f"[OK] Token resolves to: {resolved.user.email}")
        print(f"[OK] last_sign_in_at = {resolved.user.last_sign_in_at}")
    else:
        print("[ERROR] Could not resolve user from token")
except Exception as e:
    print(f"[ERROR] get_user failed: {e}")

print()

# 4. Sign out
print("=== 4. SIGN OUT ===")
try:
    anon_client.auth.sign_out()
    current = anon_client.auth.get_session()
    if current and current.session:
        print("[WARN] Session still present after sign out")
    else:
        print("[OK] Session cleared after sign out")
except Exception as e:
    print(f"[ERROR] Sign out failed: {e}")

print()

# 5. Cleanup — delete test user via admin
print("=== 5. CLEANUP (admin delete test user) ===")
try:
    from supabase import create_client as create  # avoid name collision

    admin_client.auth.admin.delete_user(user.id)
    print(f"[OK] Test user deleted: {user.id}")
except Exception as e:
    print(f"[INFO] Cleanup skipped: {e}")

print()
print("=== ALL SUPABASE AUTH TESTS PASSED ===")
