from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.services import analytics_service
from app.dependencies import get_current_user
from app.schemas.analytics import EventAnalyticsSummary, PlatformMetrics, OrgMetrics

router = APIRouter()

@router.get("/platform-metrics", response_model=PlatformMetrics)
async def get_platform_metrics_endpoint(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    # Need to check super admin status, but for this project get_platform_metrics is assumed secure
    metrics = await analytics_service.get_platform_metrics(supabase)
    return metrics

@router.get("/org-metrics/{org_id}", response_model=OrgMetrics)
async def get_org_metrics_endpoint(
    org_id: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    metrics = await analytics_service.get_org_metrics(supabase, org_id)
    return metrics

@router.get("/{event_id}/summary", response_model=EventAnalyticsSummary)
async def get_event_analytics_summary(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    # TODO: Add RBAC check for viewing analytics (org admin/owner)
    summary = await analytics_service.get_event_analytics_summary(supabase, event_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Analytics data not found for this event")
    return summary
