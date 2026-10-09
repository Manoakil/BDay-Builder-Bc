import re
from typing import Optional

def is_valid_email(email: str) -> bool:
    # Basic email validation regex
    regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"
    return re.match(regex, email) is not None

def is_valid_slug(slug: str) -> bool:
    # Slugs should be lowercase, alphanumeric, with hyphens or underscores
    regex = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    return re.match(regex, slug) is not None

def is_strong_password(password: str) -> bool:
    # Password must be at least 8 characters long, contain at least one uppercase letter, one lowercase letter, one digit, and one special character
    if len(password) < 8: return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"\d", password): return False
    if not re.search(r"[!@#$%^&*()_+=\-{\}\[\]:;\'\"<>,.?/\\|`~]", password): return False
    return True
