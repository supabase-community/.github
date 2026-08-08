"""
IronShell Core - Configuration and Clients
"""
from .config import settings
from .supabase_client import get_supabase_client
from .vector_store import VectorStoreManager

__all__ = ["settings", "get_supabase_client", "VectorStoreManager"]
