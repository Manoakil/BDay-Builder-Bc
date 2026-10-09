from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class EventAnalyticsSummary(BaseModel):
    total_visitors: int
    total_views: int
    total_wishes: int
    approved_wishes: int
    pending_wishes: int
    total_vault_attempts: int
    vault_unlocks: int
    total_shares: int
    top_countries: dict

    class Config:
        from_attributes = True

class PlatformMetrics(BaseModel):
    total_organizations: int
    active_organizations: int
    total_users: int
    total_events: int
    total_wishes: int
    total_media: int

class OrgMetrics(BaseModel):
    total_users: int
    pending_users: int
    total_wishes: int
    pending_wishes: int
    vault_enabled: bool
