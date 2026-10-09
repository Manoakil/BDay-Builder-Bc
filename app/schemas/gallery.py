from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class GalleryBase(BaseModel):
    event_id: UUID
    file_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    sort_order: int = 0
    is_featured: bool = False
    tags: Optional[list[str]] = None
    exif_data: Optional[dict] = None
    ai_tags: Optional[dict] = None
    created_by: Optional[UUID] = None
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None

class GalleryCreate(GalleryBase):
    pass

class GalleryUpdate(BaseModel):
    file_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    sort_order: Optional[int] = None
    is_featured: Optional[bool] = None
    tags: Optional[list[str]] = None
    exif_data: Optional[dict] = None
    ai_tags: Optional[dict] = None
    created_by: Optional[UUID] = None

class Gallery(GalleryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True
