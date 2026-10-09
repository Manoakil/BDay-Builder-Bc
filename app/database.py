import os
from urllib.parse import urlparse

from supabase import create_client, Client
from .config import settings

def get_supabase_client() -> Client:
    supabase_url: str = settings.SUPABASE_URL
    supabase_key: str = settings.SUPABASE_KEY
    # Some local development environments inject a dead localhost proxy.
    # Reach the configured Supabase API directly without changing proxy use
    # for any other destination.
    host = urlparse(supabase_url).hostname
    if host:
        no_proxy = {item.strip() for item in os.environ.get("NO_PROXY", "").split(",") if item.strip()}
        if host not in no_proxy:
            os.environ["NO_PROXY"] = ",".join([*no_proxy, host])
    client: Client = create_client(supabase_url, supabase_key)
    return client
