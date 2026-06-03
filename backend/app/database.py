import logging
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

def get_supabase() -> Client:
    """
    Returns a Supabase client instance.
    
    We create a new client per call rather than a singleton here —
    Supabase's Python client handles connection pooling internally.
    """
    return create_client(settings.supabase_url, settings.supabase_key)