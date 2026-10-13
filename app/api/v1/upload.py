from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.file import File, PresignedUploadRequest, PresignedUploadResponse, CompleteUploadRequest
from app.services import upload_service
from app.dependencies import get_current_user
from app.schemas.common import StorageBucket

router = APIRouter()

@router.post("/complete", response_model=File, status_code=status.HTTP_201_CREATED)
async def complete_upload(
    payload: CompleteUploadRequest,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for upload")
    
    uploaded_file = await upload_service.complete_direct_upload(
        supabase=supabase,
        bucket_name=payload.bucket,
        file_path=payload.path,
        filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        user_id=current_user.id,
        organization_id=payload.organization_id,
        event_id=payload.event_id
    )
    if not uploaded_file:
        raise HTTPException(status_code=400, detail="Failed to record uploaded file")
    return uploaded_file

@router.post("/{bucket}/presign", response_model=PresignedUploadResponse)
async def get_presigned_upload_url(
    bucket: StorageBucket,
    payload: PresignedUploadRequest,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for upload")
    
    res = upload_service.create_presigned_upload(
        supabase=supabase,
        bucket_name=bucket,
        filename=payload.filename,
        user_id=current_user.id
    )
    return res

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
