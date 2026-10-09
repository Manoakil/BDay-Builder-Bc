from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _truncate_for_bcrypt(text: str) -> str:
    text_bytes = text.encode('utf-8')
    if len(text_bytes) > 71:
        return text_bytes[:71].decode('utf-8', 'ignore')
    return text

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_truncate_for_bcrypt(plain_password), hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(_truncate_for_bcrypt(password))

def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta is not None:
        to_encode.update({"exp": datetime.utcnow() + expires_delta})
    # No 'exp' claim = token never expires (used for admin/superadmin)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_hash(plain_text: str, hashed_text: str) -> bool:
    return pwd_context.verify(_truncate_for_bcrypt(plain_text), hashed_text)
