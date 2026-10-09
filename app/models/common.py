from datetime import datetime, date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import UserStatus, MemberRole, EventStatus, EventType, EventVisibility, WishStatus, WishType, WishVisibility, CommentStatus, ReactionType, FileType, StorageBucket, NotificationType, LogAction, SubscriptionTier, SubscriptionStatus, PaymentStatus, ThemeType, FontFamily

class Role(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_system: bool
    level: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Permission(BaseModel):
    id: UUID
    name: str
    slug: str
    resource: str
    action: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class RolePermission(BaseModel):
    role_id: UUID
    permission_id: UUID
    granted_at: datetime
    granted_by: Optional[UUID]

    class Config:
        from_attributes = True

class Profile(BaseModel):
    id: UUID
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_url: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    status: UserStatus
    role_id: Optional[UUID] = None
    default_organization_id: Optional[UUID] = None
    preferences: dict = {}
    metadata: dict = {}
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None # INET type in Postgres
    login_count: int = 0
    email_verified: bool = False
    phone_verified: bool = False
    two_factor_enabled: bool = False
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    email: Optional[EmailStr] = None
    approval_status: str = "pending"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    signup_secret_code: Optional[str] = None

    class Config:
        from_attributes = True

class Organization(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[dict] = None
    subscription_tier: SubscriptionTier
    subscription_status: SubscriptionStatus
    subscription_ends_at: Optional[datetime] = None
    max_members: int = 5
    max_events: int = 1
    max_storage_mb: int = 100
    settings: dict = {}
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[UUID] = None
    deleted_at: Optional[datetime] = None
    secret_code: str
    status: str = "pending"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    auto_delete_at: Optional[datetime] = None
    auto_delete_enabled: bool = False
    deletion_warning_sent: bool = False

    class Config:
        from_attributes = True

class Invite(BaseModel):
    id: UUID
    organization_id: UUID
    email: EmailStr
    role: MemberRole
    token: str
    invited_by: Optional[UUID] = None
    message: Optional[str] = None
    status: str = "pending" # pending, accepted, expired, cancelled
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    secret_code_required: bool = True
    max_uses: int = 1
    used_count: int = 0

    class Config:
        from_attributes = True

class OrganizationMember(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: MemberRole
    permissions: list
    joined_at: datetime
    invited_by: Optional[UUID]
    invite_id: Optional[UUID]
    is_primary: bool
    metadata: dict
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True

class Event(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    event_type: EventType = EventType.birthday
    event_date: date
    event_time: Optional[str] = None # TIME type in Postgres
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
    max_wishes: int = 500
    allow_anonymous_wishes: bool = False
    moderate_wishes: bool = True
    scheduled_publish_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    view_count: int = 0
    wish_count: int = 0
    share_count: int = 0
    qr_code_url: Optional[str] = None
    short_url: Optional[str] = None
    custom_domain: Optional[str] = None
    seo_metadata: dict = {}
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[UUID] = None
    deleted_at: Optional[datetime] = None
    reveal_at: Optional[datetime] = None
    birthday_person_user_id: Optional[UUID] = None
    wishes_visible_to_bday_only: bool = False
    bday_person_approved_at: Optional[datetime] = None
    offline_package_available: bool = False
    offline_package_url: Optional[str] = None
    wishes_reveal_at: Optional[datetime] = None
    wishes_hide_until_birthday: bool = True
    allow_wisher_to_see_others: bool = False

    class Config:
        from_attributes = True

class File(BaseModel):
    id: UUID
    organization_id: Optional[UUID]
    event_id: Optional[UUID]
    bucket: StorageBucket
    path: str
    filename: str
    original_name: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    width: Optional[int]
    height: Optional[int]
    duration_seconds: Optional[float]
    file_type: FileType
    metadata: dict
    is_public: bool
    tags: Optional[list[str]]
    uploaded_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True

class Gallery(BaseModel):
    id: UUID
    event_id: UUID
    file_id: Optional[UUID]
    title: Optional[str]
    description: Optional[str]
    alt_text: Optional[str]
    sort_order: int
    is_featured: bool
    tags: Optional[list[str]]
    exif_data: Optional[dict]
    ai_tags: Optional[dict]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True

class Timeline(BaseModel):
    id: UUID
    event_id: UUID
    title: str
    description: Optional[str]
    entry_date: date
    entry_time: Optional[str] # TIME type in Postgres
    location: Optional[str]
    file_id: Optional[UUID]
    sort_order: int
    is_milestone: bool
    age_at_time: Optional[float]
    category: Optional[str]
    tags: Optional[list[str]]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True

class Wish(BaseModel):
    id: UUID
    event_id: UUID
    user_id: Optional[UUID] = None
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
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    wisher_name: Optional[str] = None
    relation_to_bday_person: Optional[str] = None
    updated_by: Optional[UUID] = None
    wisher_display_name: Optional[str] = None
    visible_to_wishers: bool = False
    visible_to_bday: bool = True
    visible_to_admin: bool = True
    show_wisher_identity: bool = True

    class Config:
        from_attributes = True

class Comment(BaseModel):
    id: UUID
    wish_id: UUID
    user_id: Optional[UUID]
    guest_name: Optional[str]
    content: str
    status: CommentStatus
    parent_comment_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True

class Reaction(BaseModel):
    id: UUID
    wish_id: UUID
    user_id: Optional[UUID]
    guest_identifier: Optional[str]
    reaction_type: ReactionType
    created_at: datetime

    class Config:
        from_attributes = True

class SecretVault(BaseModel):
    id: UUID
    event_id: UUID
    question: str
    answer_hash: str
    hint: Optional[str] = None
    unlock_message: Optional[str] = None
    unlock_media_url: Optional[str] = None
    max_attempts: int = 3
    current_attempts: int = 0
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    unlock_time: Optional[datetime] = None
    auto_unlock_enabled: bool = False
    auto_unlock_at: Optional[datetime] = None
    unlock_count: int = 0
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    vault_wish_id: Optional[UUID] = None
    is_enabled: bool = True
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    media_photos: list[str] = []
    media_videos: list[str] = []
    media_audio: list[str] = []
    media_description: Optional[str] = None
    dynamic_data: dict = {}

    class Config:
        from_attributes = True

class VaultAttempt(BaseModel):
    id: UUID
    vault_id: UUID
    user_id: Optional[UUID]
    guest_identifier: Optional[str]
    attempt_answer: str
    is_correct: bool
    ip_address: Optional[str] # INET type in Postgres
    user_agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class Notification(BaseModel):
    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    message: Optional[str]
    data: dict
    is_read: bool
    read_at: Optional[datetime]
    action_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLog(BaseModel):
    id: UUID
    organization_id: Optional[UUID]
    event_id: Optional[UUID]
    user_id: Optional[UUID]
    action: LogAction
    table_name: str
    record_id: Optional[UUID]
    old_data: Optional[dict]
    new_data: Optional[dict]
    ip_address: Optional[str] # INET type in Postgres
    user_agent: Optional[str]
    metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True

class AnalyticsEvent(BaseModel):
    id: UUID
    event_id: UUID
    visitor_id: Optional[str]
    session_id: Optional[str]
    page_url: Optional[str]
    referrer: Optional[str]
    event_name: str
    event_data: dict
    device_type: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    country: Optional[str]
    city: Optional[str]
    ip_address: Optional[str] # INET type in Postgres
    user_agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AnalyticsDaily(BaseModel):
    id: UUID
    event_id: UUID
    date: date
    unique_visitors: int
    page_views: int
    wish_submissions: int
    wish_approvals: int
    vault_attempts: int
    vault_unlocks: int
    shares: int
    avg_session_duration: Optional[float]
    bounce_rate: Optional[float]
    countries_data: dict
    devices_data: dict
    created_at: datetime

    class Config:
        from_attributes = True

class Subscription(BaseModel):
    id: UUID
    organization_id: UUID
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    canceled_at: Optional[datetime]
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    payment_provider: Optional[str]
    provider_subscription_id: Optional[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Payment(BaseModel):
    id: UUID
    organization_id: Optional[UUID]
    subscription_id: Optional[UUID]
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: Optional[str]
    provider_payment_id: Optional[str]
    invoice_url: Optional[str]
    paid_at: Optional[datetime]
    refunded_at: Optional[datetime]
    metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True

class Theme(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    type: ThemeType
    is_premium: bool
    price: float
    preview_url: Optional[str]
    settings: dict
    created_by: Optional[UUID]
    is_public: bool
    download_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrganizationTheme(BaseModel):
    id: UUID
    organization_id: UUID
    theme_id: UUID
    is_active: bool
    custom_settings: Optional[dict] = None
    purchased_at: datetime

    class Config:
        from_attributes = True

class ApprovalWorkflow(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    approver_id: Optional[UUID] = None
    entity_type: str
    entity_id: UUID
    status: str = "pending"
    request_data: dict = {}
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DownloadPackage(BaseModel):
    id: UUID
    event_id: UUID
    organization_id: UUID
    package_type: str = "offline"
    package_url: str
    size_bytes: Optional[int] = None
    includes_wishes: bool = True
    includes_gallery: bool = True
    includes_timeline: bool = True
    includes_vault_content: bool = False
    generated_at: datetime
    expires_at: Optional[datetime] = None
    downloaded_count: int = 0
    created_by: Optional[UUID] = None

    class Config:
        from_attributes = True

class AutoDeleteSchedule(BaseModel):
    id: UUID
    organization_id: UUID
    entity_type: str
    entity_id: Optional[UUID] = None
    delete_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    notification_sent: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class VaultMedia(BaseModel):
    id: UUID
    vault_id: UUID
    file_id: UUID
    media_type: str # photo, video, audio
    sort_order: int = 0
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class WishViewLog(BaseModel):
    id: UUID
    wish_id: UUID
    viewer_id: Optional[UUID] = None
    viewer_role: Optional[str] = None
    viewed_at: datetime

    class Config:
        from_attributes = True


