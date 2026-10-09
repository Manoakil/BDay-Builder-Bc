from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
from app.database import get_supabase_client
from app.config import settings


async def _get_user_from_token(supabase, token: str):
    """Standalone helper usable outside FastAPI dependency injection."""
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM],
        options={"verify_exp": False}
    )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_response = supabase.auth.get_user(token)
    if not user_response.user or str(user_response.user.id) != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    return user_response.user


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/register-with-code",
            "/", "/docs", "/openapi.json"
        ] or (request.url.path.startswith("/api/v1/events/") and request.method == "GET"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(content="Not authenticated", status_code=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(" ")[1]
        try:
            supabase = get_supabase_client()
            request.state.user = await _get_user_from_token(supabase, token)
        except HTTPException as e:
            return Response(content=e.detail, status_code=e.status_code)
        except Exception:
            return Response(content="Internal server error during authentication", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return await call_next(request)
