from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.schemas.common import WishType, WishStatus, WishVisibility, ReactionType, CommentStatus, FileType, StorageBucket

class WishBase(BaseModel):
    event_id: Optional[UUID] = None  # Auto-assigned from user's org if not provided
    user_id: Optional[UUID] = None
    wisher_name: Optional[str] = None          # Name entered by the wisher
    relation_to_bday_person: Optional[str] = None  # e.g. friend, sibling, colleague
    guest_name: Optional[str] = None
    guest_email: Optional[EmailStr] = None
    wish_type: WishType = WishType.text
    content: Optional[str] = None
    file_id: Optional[UUID] = None
    visibility: WishVisibility = WishVisibility.normal
    status: WishStatus = WishStatus.pending
    is_anonymous: bool = False
    is_featured: bool = False
    scheduled_for: Optional[datetime] = None
    ai_generated: bool = False
    ai_prompt: Optional[str] = None
    language: str = "en"
    sentiment_score: Optional[float] = None
    reply_count: int = 0
    reaction_counts: dict = {}
    updated_by: Optional[UUID] = None
    wisher_display_name: Optional[str] = None
    visible_to_wishers: bool = False
    visible_to_bday: bool = True
    visible_to_admin: bool = True
    show_wisher_identity: bool = True
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None

class WishCreate(WishBase):
    pass

class WishUpdate(BaseModel):
    content: Optional[str] = None
    file_id: Optional[UUID] = None
    visibility: Optional[WishVisibility] = None
    status: Optional[WishStatus] = None
    is_anonymous: Optional[bool] = None
    is_featured: Optional[bool] = None
    scheduled_for: Optional[datetime] = None
    ai_generated: Optional[bool] = None
    ai_prompt: Optional[str] = None
    language: Optional[str] = None
    sentiment_score: Optional[float] = None
    reply_count: Optional[int] = None
    reaction_counts: Optional[dict] = None
    wisher_name: Optional[str] = None
    relation_to_bday_person: Optional[str] = None
    updated_by: Optional[UUID] = None
    wisher_display_name: Optional[str] = None
    visible_to_wishers: Optional[bool] = None
    visible_to_bday: Optional[bool] = None
    visible_to_admin: Optional[bool] = None
    show_wisher_identity: Optional[bool] = None

class Wish(WishBase):
    id: UUID
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CommentBase(BaseModel):
    wish_id: UUID
    user_id: Optional[UUID] = None
    guest_name: Optional[str] = None
    content: str
    status: CommentStatus = CommentStatus.active
    parent_comment_id: Optional[UUID] = None

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[CommentStatus] = None

class Comment(CommentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ReactionCreate(BaseModel):
    wish_id: UUID
    user_id: Optional[UUID] = None
    guest_identifier: Optional[str] = None
    reaction_type: ReactionType

class Reaction(ReactionCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class WishViewLogBase(BaseModel):
    wish_id: UUID
    viewer_id: Optional[UUID] = None
    viewer_role: Optional[str] = None

class WishViewLogCreate(WishViewLogBase):
    pass

class WishViewLog(WishViewLogBase):
    id: UUID
    viewed_at: datetime

    class Config:
        from_attributes = True
