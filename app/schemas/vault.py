from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class SecretVaultBase(BaseModel):
    event_id: UUID
    question: str
    answer_hash: str
    hint: Optional[str] = None
    unlock_message: Optional[str] = None
    unlock_media_url: Optional[str] = None
    vault_wish_id: Optional[UUID] = None   # The one special wish revealed after unlock
    max_attempts: int = 3
    current_attempts: int = 0
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    unlock_time: Optional[datetime] = None
    auto_unlock_enabled: bool = False
    auto_unlock_at: Optional[datetime] = None
    unlock_count: int = 0
    created_by: Optional[UUID] = None
    is_enabled: bool = True
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    media_photos: list[str] = []
    media_videos: list[str] = []
    media_audio: list[str] = []
    media_description: Optional[str] = None
    dynamic_data: dict = {}

class SecretVaultCreate(SecretVaultBase):
    pass

class SecretVaultUpdate(BaseModel):
    question: Optional[str] = None
    answer_hash: Optional[str] = None
    hint: Optional[str] = None
    unlock_message: Optional[str] = None
    unlock_media_url: Optional[str] = None
    vault_wish_id: Optional[UUID] = None
    max_attempts: Optional[int] = None
    current_attempts: Optional[int] = None
    is_locked: Optional[bool] = None
    locked_until: Optional[datetime] = None
    unlock_time: Optional[datetime] = None
    auto_unlock_enabled: Optional[bool] = None
    auto_unlock_at: Optional[datetime] = None
    unlock_count: Optional[int] = None
    created_by: Optional[UUID] = None
    is_enabled: Optional[bool] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    media_photos: Optional[list[str]] = None
    media_videos: Optional[list[str]] = None
    media_audio: Optional[list[str]] = None
    media_description: Optional[str] = None
    dynamic_data: Optional[dict] = None

class SecretVault(SecretVaultBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SecretVaultPublic(BaseModel):
    """Safe vault payload for the birthday person; never expose answer_hash."""
    id: UUID
    question: str
    hint: Optional[str] = None
    unlock_message: Optional[str] = None
    unlock_media_url: Optional[str] = None
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    auto_unlock_enabled: bool = False
    auto_unlock_at: Optional[datetime] = None
    is_enabled: bool = True
    media_photos: list[str] = []
    media_videos: list[str] = []
    media_audio: list[str] = []
    media_description: Optional[str] = None
    dynamic_data: dict = {}

class VaultAttemptCreate(BaseModel):
    vault_id: UUID
    user_id: Optional[UUID] = None
    guest_identifier: Optional[str] = None
    attempt_answer: str
    is_correct: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class VaultAttempt(VaultAttemptCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class VaultMediaBase(BaseModel):
    vault_id: UUID
    file_id: UUID
    media_type: str # photo, video, audio
    sort_order: int = 0
    title: Optional[str] = None
    description: Optional[str] = None

class VaultMediaCreate(VaultMediaBase):
    pass

class VaultMediaUpdate(BaseModel):
    media_type: Optional[str] = None
    sort_order: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None

class VaultMedia(VaultMediaBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
