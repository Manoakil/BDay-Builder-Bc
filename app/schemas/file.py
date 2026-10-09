from typing import Optional
from uuid import UUID
from datetime import datetime, date, time
from pydantic import BaseModel, EmailStr

from app.schemas.common import FileType, StorageBucket

class FileBase(BaseModel):
    organization_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    bucket: StorageBucket
    path: str
    filename: str
    original_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    file_type: FileType = FileType.image
    metadata: dict = {}
    is_public: bool = False
    tags: Optional[list[str]] = None
    uploaded_by: Optional[UUID] = None

class FileCreate(FileBase):
    pass

class FileUpdate(BaseModel):
    organization_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    bucket: Optional[StorageBucket] = None
    path: Optional[str] = None
    filename: Optional[str] = None
    original_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    file_type: Optional[FileType] = None
    metadata: Optional[dict] = None
    is_public: Optional[bool] = None
    tags: Optional[list[str]] = None
    uploaded_by: Optional[UUID] = None

class File(FileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True
