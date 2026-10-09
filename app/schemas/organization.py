from typing import Optional
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, EmailStr

from app.schemas.common import MemberRole, SubscriptionTier, SubscriptionStatus

class OrganizationBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[dict] = None

class OrganizationCreate(OrganizationBase):
    # The authenticated endpoint assigns this; clients must never supply it.
    created_by: Optional[UUID] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[dict] = None
    subscription_tier: Optional[SubscriptionTier] = None
    subscription_status: Optional[SubscriptionStatus] = None
    max_members: Optional[int] = None
    max_events: Optional[int] = None
    max_storage_mb: Optional[int] = None
    settings: Optional[dict] = None
    updated_by: Optional[UUID] = None
    secret_code: Optional[str] = None
    status: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    auto_delete_at: Optional[datetime] = None
    auto_delete_enabled: Optional[bool] = None
    deletion_warning_sent: Optional[bool] = None

class Organization(OrganizationBase):
    id: UUID
    secret_code: str  # Admin shares this with wishers/birthday person
    subscription_tier: SubscriptionTier
    subscription_status: SubscriptionStatus
    subscription_ends_at: Optional[datetime]
    max_members: int
    max_events: int
    max_storage_mb: int
    settings: dict
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[UUID]
    deleted_at: Optional[datetime]
    status: str = "pending"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    auto_delete_at: Optional[datetime] = None
    auto_delete_enabled: bool = False
    deletion_warning_sent: bool = False

    class Config:
        from_attributes = True

class InviteCreate(BaseModel):
    organization_id: UUID
    email: EmailStr
    role: MemberRole = MemberRole.viewer
    invited_by: UUID
    message: Optional[str] = None
    expires_at: Optional[datetime] = None
    secret_code_required: bool = True
    max_uses: int = 1

class Invite(BaseModel):
    id: UUID
    organization_id: UUID
    email: EmailStr
    role: MemberRole
    token: str
    invited_by: Optional[UUID]
    message: Optional[str]
    status: str
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    secret_code_required: bool = True
    max_uses: int = 1
    used_count: int = 0

    class Config:
        from_attributes = True

class OrganizationMemberCreate(BaseModel):
    organization_id: UUID
    user_id: UUID
    role: MemberRole = MemberRole.viewer
    invited_by: Optional[UUID] = None
    invite_id: Optional[UUID] = None
    is_primary: bool = False
    permissions: list = []
    metadata: dict = {}

class OrganizationMemberUpdate(BaseModel):
    role: Optional[MemberRole] = None
    permissions: Optional[list] = None
    is_primary: Optional[bool] = None
    metadata: Optional[dict] = None

class OrganizationMember(OrganizationMemberCreate):
    id: UUID
    joined_at: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True

class ApprovalWorkflowBase(BaseModel):
    organization_id: UUID
    user_id: UUID
    approver_id: Optional[UUID] = None
    entity_type: str
    entity_id: UUID
    status: str = "pending"
    request_data: dict = {}

class ApprovalWorkflowCreate(ApprovalWorkflowBase):
    pass

class ApprovalWorkflowUpdate(BaseModel):
    status: Optional[str] = None
    approver_id: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    request_data: Optional[dict] = None

class ApprovalWorkflow(ApprovalWorkflowBase):
    id: UUID
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AutoDeleteScheduleBase(BaseModel):
    organization_id: UUID
    entity_type: str
    entity_id: Optional[UUID] = None
    delete_at: datetime
    is_deleted: bool = False
    notification_sent: bool = False

class AutoDeleteScheduleCreate(AutoDeleteScheduleBase):
    pass

class AutoDeleteScheduleUpdate(BaseModel):
    delete_at: Optional[datetime] = None
    is_deleted: Optional[bool] = None
    deleted_at: Optional[datetime] = None
    notification_sent: Optional[bool] = None

class AutoDeleteSchedule(AutoDeleteScheduleBase):
    id: UUID
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
