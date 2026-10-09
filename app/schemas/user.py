from typing import Optional
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, EmailStr

from app.schemas.common import UserStatus, MemberRole, EventStatus, EventType, EventVisibility, WishStatus, WishType, WishVisibility, CommentStatus, ReactionType, FileType, StorageBucket, NotificationType, LogAction, SubscriptionTier, SubscriptionStatus, PaymentStatus, ThemeType, FontFamily

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    full_name: Optional[str] = None

class User(UserBase):
    id: UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: UserStatus
    role_id: Optional[UUID] = None
    role_slug: Optional[str] = None
    created_at: datetime
    approval_status: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_of_birth: Optional[date] = None

    class Config:
        from_attributes = True

class ProfileCreate(BaseModel):
    id: UUID
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    status: UserStatus = UserStatus.pending_approval
    role_id: Optional[UUID] = None
    default_organization_id: Optional[UUID] = None
    preferences: dict = {}
    metadata: dict = {}
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    login_count: int = 0
    email_verified: bool = False
    phone_verified: bool = False
    two_factor_enabled: bool = False
    email: Optional[EmailStr] = None
    approval_status: str = "pending"
    signup_secret_code: Optional[str] = None

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    status: Optional[UserStatus] = None
    role_id: Optional[UUID] = None
    default_organization_id: Optional[UUID] = None
    preferences: Optional[dict] = None
    metadata: Optional[dict] = None
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    login_count: Optional[int] = None
    email_verified: Optional[bool] = None
    phone_verified: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None
    email: Optional[EmailStr] = None
    approval_status: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

class Profile(ProfileCreate):
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    class Config:
        from_attributes = True
