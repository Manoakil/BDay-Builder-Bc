from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.schemas.common import ThemeType, FontFamily

class ThemeBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    type: ThemeType = ThemeType.preset
    is_premium: bool = False
    price: float = 0.0
    preview_url: Optional[str] = None
    settings: dict = {}
    created_by: Optional[UUID] = None
    is_public: bool = True
    download_count: int = 0

class ThemeCreate(ThemeBase):
    pass

class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    type: Optional[ThemeType] = None
    is_premium: Optional[bool] = None
    price: Optional[float] = None
    preview_url: Optional[str] = None
    settings: Optional[dict] = None
    is_public: Optional[bool] = None
    download_count: Optional[int] = None

class Theme(ThemeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrganizationThemeBase(BaseModel):
    organization_id: UUID
    theme_id: UUID
    is_active: bool = False
    custom_settings: Optional[dict] = None

class OrganizationThemeCreate(OrganizationThemeBase):
    pass

class OrganizationThemeUpdate(BaseModel):
    is_active: Optional[bool] = None
    custom_settings: Optional[dict] = None

class OrganizationTheme(OrganizationThemeBase):
    id: UUID
    purchased_at: datetime

    class Config:
        from_attributes = True
