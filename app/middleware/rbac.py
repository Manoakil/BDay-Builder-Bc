from typing import Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.auth_service import get_user_by_id
from app.database import get_supabase_client
from app.config import settings

class RBACMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip for public routes or if user is not authenticated
        if not hasattr(request.state, 'user') or request.url.path in ["/api/v1/auth/login", "/api/v1/auth/register", "/", "/docs", "/openapi.json"] or request.url.path.startswith("/api/v1/events/") and request.method == "GET":
            response = await call_next(request)
            return response

        user = request.state.user
        required_permission = self._get_required_permission(request.method, request.url.path)
        
        if required_permission:
            supabase = get_supabase_client()
            # This is a placeholder. In a real app, you'd fetch user's roles and then check permissions
            # For now, let's assume only 'super_admin' has all permissions for demonstration
            profile_response = supabase.from_('profiles').select('role_id').eq('id', user.id).single().execute()
            user_role_id = profile_response.data['role_id'] if profile_response.data else None

            if user_role_id:
                role_response = supabase.from_('roles').select('slug').eq('id', user_role_id).single().execute()
                role_slug = role_response.data['slug'] if role_response.data else None

                if role_slug in settings.PERMANENT_ROLES:  # admin and super_admin always have access
                    pass
                else:
                    # Implement more granular permission checks here based on required_permission
                    # For example, checking role_permissions table
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no assigned role")
        
        response = await call_next(request)
        return response

    def _get_required_permission(self, method: str, path: str) -> Optional[str]:
        # This is a very simplistic mapping. In a real app, use decorators or a more robust system.
        if "/organizations" in path:
            if method == "POST": return "create_organizations"
            if method == "PUT": return "manage_organizations"
            if method == "GET": return "view_organizations"
        if "/events" in path:
            if method == "POST": return "create_events"
            if method == "PUT": return "edit_events"
            if method == "DELETE": return "delete_events"
        # Add more mappings as needed
        return None
