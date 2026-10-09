from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.file import File
from app.services import upload_service
from app.dependencies import get_current_user
from app.schemas.common import StorageBucket

router = APIRouter()

@router.post("/{bucket}", response_model=File, status_code=status.HTTP_201_CREATED)
async def upload_file(
    bucket: StorageBucket,
    file: UploadFile = FastAPIFile(...),
    organization_id: Optional[UUID] = None, # Optional: if uploading for an organization
    event_id: Optional[UUID] = None, # Optional: if uploading for an event
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for upload")
    
    uploaded_file = await upload_service.upload_file(
        supabase=supabase,
        bucket_name=bucket,
        file=file,
        user_id=current_user.id,
        organization_id=organization_id,
        event_id=event_id
    )
    if not uploaded_file:
        raise HTTPException(status_code=400, detail="File upload failed")
    return uploaded_file

# TODO: Add endpoints for deleting files, getting file metadata, etc.
