from typing import Optional
from uuid import UUID
from datetime import datetime, date, time
from pydantic import BaseModel

from app.schemas.common import EventType, EventStatus, EventVisibility

class EventBase(BaseModel):
    organization_id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    event_type: EventType = EventType.birthday
    event_date: date
    event_time: Optional[time] = None
    timezone: str = "UTC"
    location: Optional[dict] = None
    status: EventStatus = EventStatus.draft
    visibility: EventVisibility = EventVisibility.private
    access_password: Optional[str] = None
    cover_url: Optional[str] = None
    hero_video_url: Optional[str] = None
    background_music_url: Optional[str] = None
    theme_settings: dict = {}
    module_settings: dict = {}
    reveal_sequence: list = []
    birthday_person_name: Optional[str] = None
    birthday_person_photo: Optional[str] = None
    birthday_person_bio: Optional[str] = None
    birthday_person_user_id: Optional[UUID] = None
    reveal_at: Optional[datetime] = None  # Wishes unlock at this time (e.g. 12:00 AM on bday)
    wishes_visible_to_bday_only: bool = False
    bday_person_approved_at: Optional[datetime] = None
    offline_package_available: bool = False
    offline_package_url: Optional[str] = None
    wishes_reveal_at: Optional[datetime] = None
    wishes_hide_until_birthday: bool = True
    allow_wisher_to_see_others: bool = False
    max_wishes: int = 500
    allow_anonymous_wishes: bool = False
    moderate_wishes: bool = True
    scheduled_publish_at: Optional[datetime] = None
    qr_code_url: Optional[str] = None
    short_url: Optional[str] = None
    custom_domain: Optional[str] = None
    seo_metadata: dict = {}

class EventCreate(EventBase):
    created_by: UUID

class EventUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    event_date: Optional[date] = None
    event_time: Optional[time] = None
    timezone: Optional[str] = None
    location: Optional[dict] = None
    status: Optional[EventStatus] = None
    visibility: Optional[EventVisibility] = None
    access_password: Optional[str] = None
    cover_url: Optional[str] = None
    hero_video_url: Optional[str] = None
    background_music_url: Optional[str] = None
    theme_settings: Optional[dict] = None
    module_settings: Optional[dict] = None
    reveal_sequence: Optional[list] = None
    birthday_person_name: Optional[str] = None
    birthday_person_photo: Optional[str] = None
    birthday_person_bio: Optional[str] = None
    birthday_person_user_id: Optional[UUID] = None
    reveal_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    wishes_visible_to_bday_only: Optional[bool] = None
    bday_person_approved_at: Optional[datetime] = None
    offline_package_available: Optional[bool] = None
    offline_package_url: Optional[str] = None
    wishes_reveal_at: Optional[datetime] = None
    wishes_hide_until_birthday: Optional[bool] = None
    allow_wisher_to_see_others: Optional[bool] = None
    max_wishes: Optional[int] = None
    allow_anonymous_wishes: Optional[bool] = None
    moderate_wishes: Optional[bool] = None
    scheduled_publish_at: Optional[datetime] = None
    qr_code_url: Optional[str] = None
    short_url: Optional[str] = None
    custom_domain: Optional[str] = None
    seo_metadata: Optional[dict] = None
    updated_by: Optional[UUID] = None

class Event(EventBase):
    id: UUID
    published_at: Optional[datetime]
    expires_at: Optional[datetime]
    view_count: int
    wish_count: int
    share_count: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[UUID]
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True

class DownloadPackageBase(BaseModel):
    event_id: UUID
    organization_id: UUID
    package_type: str = "offline"
    package_url: str
    size_bytes: Optional[int] = None
    includes_wishes: bool = True
    includes_gallery: bool = True
    includes_timeline: bool = True
    includes_vault_content: bool = False
    expires_at: Optional[datetime] = None
    created_by: Optional[UUID] = None

class DownloadPackageCreate(DownloadPackageBase):
    pass

class DownloadPackageUpdate(BaseModel):
    package_url: Optional[str] = None
    size_bytes: Optional[int] = None
    expires_at: Optional[datetime] = None
    downloaded_count: Optional[int] = None

class DownloadPackage(DownloadPackageBase):
    id: UUID
    generated_at: datetime
    downloaded_count: int = 0

    class Config:
        from_attributes = True
