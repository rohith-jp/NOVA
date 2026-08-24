from supabase import Client, create_client
from app.core.config import settings

_supabase_client: Client | None = None
_supabase_admin_client: Client | None = None


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment")
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase_client


def get_supabase_admin_client() -> Client:
    global _supabase_admin_client
    if _supabase_admin_client is None:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        if not settings.SUPABASE_URL or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment"
            )
        _supabase_admin_client = create_client(settings.SUPABASE_URL, key)
    return _supabase_admin_client


def check_supabase_connection() -> bool:
    try:
        client = get_supabase_admin_client()
        # Ping Supabase REST API endpoint or Auth health
        return client is not None
    except Exception:
        return False
