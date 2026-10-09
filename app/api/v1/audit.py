from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.services import organization_service

router = APIRouter()

class AuditLog(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    details: dict = {}
    ip_address: str = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[AuditLog])
async def get_audit_logs(
    supabase=Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
):
    if not organization_service.is_super_admin(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin can view global audit logs"
        )
    
    res = supabase.table('audit_logs').select('*').order('created_at', desc=True).limit(100).execute()
    return res.data
