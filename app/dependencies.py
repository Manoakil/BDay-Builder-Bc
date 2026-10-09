from typing import Generator
from types import SimpleNamespace
from uuid import UUID
import psycopg2
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from supabase import Client
from .database import get_supabase_client
from .config import settings
from .schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    supabase: Client = Depends(get_supabase_client),
    token: str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}  # exp is optional; admin/superadmin tokens have no exp
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    # The login endpoint issues this application's JWT, so Supabase cannot verify
    # its signature. Preserve the user-existence check through the server-side DB.
    # Use Supabase REST API instead of psycopg2 to bypass direct DB DNS issues.
    try:
        from supabase import create_client
        service_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_STORAGE_SERVICE_ROLE_KEY)
        response = service_client.from_('profiles').select('id').eq('id', token_data.user_id).execute()
        
        if not response.data:
            raise credentials_exception
            
        return SimpleNamespace(id=UUID(token_data.user_id), role=payload.get("role"))
    except Exception as e:
        print(f"Error in user existence check: {e}")
        raise credentials_exception
