"""NOVA centralized settings.

All environment variables are declared here so there is one authoritative
place to check what the backend needs. Individual modules should import from
this module rather than calling os.getenv() directly.

Railway and local dev both inject variables through the process environment;
python-dotenv loads .env only when running locally (load_dotenv is a no-op
if the vars are already set, so it is safe in production too).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # ── Database (direct psycopg2 — used for migrations) ─────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ── Redis / Upstash ───────────────────────────────────────
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # ── AI — Google Gemini ────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ── AI — Anthropic Claude ─────────────────────────────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # ── AI — Groq ─────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # ── AI — OpenAI (Whisper STT) ─────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ── Search — Tavily ───────────────────────────────────────
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # ── Voice — ElevenLabs TTS ───────────────────────────────
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    # ── Security — field-level encryption ────────────────────
    # Must be set explicitly in production. Do NOT rely on the fallback.
    ENCRYPTION_SECRET_KEY: str = os.getenv("ENCRYPTION_SECRET_KEY", "")

    # ── CORS ──────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g.:
    #   https://your-app.vercel.app,https://nova.yourdomain.com
    CORS_ALLOWED_ORIGINS: str = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )

    # ── Application URLs ──────────────────────────────────────
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")


settings = Settings()
