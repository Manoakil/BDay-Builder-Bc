from typing import Optional
from uuid import UUID
from datetime import datetime, date, time
from pydantic import BaseModel

class TimelineBase(BaseModel):
    event_id: Optional[UUID] = None  # Auto-assigned from user's org if not provided
    title: str
    description: Optional[str] = None
    entry_date: date
    entry_time: Optional[time] = None
    location: Optional[str] = None
    file_id: Optional[UUID] = None
    sort_order: int = 0
    is_milestone: bool = False
    age_at_time: Optional[float] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    created_by: Optional[UUID] = None
    # Derived from the attached files row when timeline entries are read.
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None

class TimelineCreate(TimelineBase):
    pass

class TimelineUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    entry_date: Optional[date] = None
    entry_time: Optional[time] = None
    location: Optional[str] = None
    file_id: Optional[UUID] = None
    sort_order: Optional[int] = None
    is_milestone: Optional[bool] = None
    age_at_time: Optional[float] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    created_by: Optional[UUID] = None

class Timeline(TimelineBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True
