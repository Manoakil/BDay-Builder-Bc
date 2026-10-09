from typing import Any, Dict
from uuid import UUID

def clean_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Removes None values from a dictionary."""
    return {k: v for k, v in data.items() if v is not None}

def generate_short_code(length: int = 8) -> str:
    """Generates a random alphanumeric short code."""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))
