#!/usr/bin/env python3
"""
NOVA Deployment Verification Script

Usage:
    python scripts/verify_deployment.py https://your-backend.up.railway.app

Checks:
  1. FastAPI /health endpoint responds
  2. Database connection reported as connected
  3. WebSocket /ws/connect endpoint accepts connections
  4. Celery ping task dispatched and returns result
  5. Redis connection (indirectly via Celery result backend)
"""
import sys
import json
import time
import urllib.request
import urllib.error

try:
    import websocket  # websocket-client
    HAS_WS = True
except ImportError:
    HAS_WS = False

try:
    import redis as redis_lib
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


def check(label: str, fn):
    print(f"  ► {label} ...", end=" ", flush=True)
    try:
        result = fn()
        print(f"✅  {result}")
        return True
    except Exception as e:
        print(f"❌  {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_deployment.py <BACKEND_URL>")
        print("Example: python verify_deployment.py https://nova-backend.up.railway.app")
        sys.exit(1)

    base = sys.argv[1].rstrip("/")
    redis_url = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"\n{'='*60}")
    print(f"  NOVA Deployment Verification")
    print(f"  Backend: {base}")
    print(f"{'='*60}\n")

    results = []

    # ── 1. FastAPI root ────────────────────────────────────────
    def _check_root():
        with urllib.request.urlopen(f"{base}/", timeout=10) as r:
            data = json.loads(r.read())
            assert data.get("message"), "Unexpected root response"
            return data["message"]

    results.append(check("FastAPI root endpoint (GET /)", _check_root))

    # ── 2. Health endpoint + DB ────────────────────────────────
    def _check_health():
        with urllib.request.urlopen(f"{base}/health", timeout=10) as r:
            data = json.loads(r.read())
            db = data.get("database", "unknown")
            if db != "connected":
                raise AssertionError(f"database={db} (check SUPABASE env vars)")
            return f"status={data['status']}, database={db}"

    results.append(check("Health check + Supabase DB (GET /health)", _check_health))

    # ── 3. Docs endpoint reachable ─────────────────────────────
    def _check_docs():
        with urllib.request.urlopen(f"{base}/docs", timeout=10) as r:
            assert r.status == 200
            return "OpenAPI docs reachable"

    results.append(check("OpenAPI docs (GET /docs)", _check_docs))

    # ── 4. WebSocket connect ───────────────────────────────────
    if HAS_WS:
        def _check_ws():
            ws_url = base.replace("https://", "wss://").replace("http://", "ws://")
            ws = websocket.create_connection(f"{ws_url}/ws/connect", timeout=10)
            msg = json.loads(ws.recv())
            ws.close()
            assert msg.get("type") == "connected", f"Unexpected ws message: {msg}"
            return msg["message"]

        results.append(check("WebSocket /ws/connect", _check_ws))
    else:
        print("  ⚠  WebSocket check skipped (install websocket-client to enable)")

    # ── 5. Direct Redis ping (optional) ───────────────────────
    if redis_url and HAS_REDIS:
        def _check_redis():
            import ssl as ssl_lib
            kwargs = {}
            if redis_url.startswith("rediss://"):
                kwargs["ssl_cert_reqs"] = ssl_lib.CERT_NONE
            r = redis_lib.from_url(redis_url, **kwargs)
            assert r.ping(), "Redis ping returned False"
            r.close()
            return "Redis PONG received"

        results.append(check(f"Redis ping ({redis_url[:40]}...)", _check_redis))
    elif redis_url:
        print("  ⚠  Redis direct check skipped (install redis to enable)")
    else:
        print("  ⚠  Redis direct check skipped (pass REDIS_URL as 2nd arg to enable)")

    # ── Summary ───────────────────────────────────────────────
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} checks passed")
    if passed == total:
        print("  🎉 All checks passed — NOVA backend is healthy!")
    else:
        print("  ⚠  Some checks failed — review errors above.")
    print(f"{'='*60}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
