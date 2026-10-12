import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings

def _truncate_for_bcrypt(text: str) -> bytes:
    text_bytes = text.encode('utf-8')
    if len(text_bytes) > 71:
        return text_bytes[:71]
    return text_bytes

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate_for_bcrypt(plain_password), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(_truncate_for_bcrypt(password), salt).decode('utf-8')

def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta is not None:
        to_encode.update({"exp": datetime.utcnow() + expires_delta})
    # No 'exp' claim = token never expires (used for admin/superadmin)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_hash(plain_text: str, hashed_text: str) -> bool:
    try:
        if hashed_text.startswith('$2b$') or hashed_text.startswith('$2a$') or hashed_text.startswith('$2y$'):
            return bcrypt.checkpw(_truncate_for_bcrypt(plain_text), hashed_text.encode('utf-8'))
    except Exception:
        pass
    return plain_text.strip().lower() == hashed_text.strip().lower()
