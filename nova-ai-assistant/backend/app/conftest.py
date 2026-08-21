"""
pytest configuration for NOVA backend tests.

- Unit tests run always (no markers needed).
- Tests marked @pytest.mark.integration are skipped in CI unless
  the environment variable RUN_INTEGRATION_TESTS=1 is set.
- Tests that import live clients (Gemini, Supabase DB writes) are
  collected under the integration marker automatically via the
  path patterns in pytest.ini.
"""
import os
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring live external services",
    )


def pytest_collection_modifyitems(config, items):
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"
    skip_integration = pytest.mark.skip(
        reason="Integration test skipped in CI. Set RUN_INTEGRATION_TESTS=1 to run."
    )
    for item in items:
        # Auto-skip known live-API test files
        integration_files = {
            "test_gemini.py",
            "test_planner.py",   # calls real Gemini
            "test_memory.py",    # writes to real Supabase
            "test_auth.py",      # hits real Supabase auth
            "test_jwt_auth.py",  # hits real Supabase auth
            "test_schema.py",    # needs real DB
            "test_browser.py",   # needs running Celery + Redis
            "test_voice.py",     # calls real ElevenLabs / Whisper
            "test_ws_stream.py", # needs Gemini for live stream
        }
        if item.fspath.basename in integration_files:
            if not run_integration:
                item.add_marker(skip_integration)
