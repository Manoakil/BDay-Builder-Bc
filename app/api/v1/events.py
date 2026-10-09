from typing import List, Any
from uuid import UUID
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.event import Event, EventCreate, EventUpdate
from app.services import event_service
from app.services import organization_service
from app.dependencies import get_current_user

router = APIRouter()


def _reveal_time(event: Event) -> datetime:
    """The celebration never opens before the birthday, even if an older
    event has an earlier reveal_at value."""
    try:
        event_tz = ZoneInfo(event.timezone or "UTC")
    except Exception:
        event_tz = timezone.utc
    birthday_start = datetime.combine(event.event_date, datetime.min.time(), tzinfo=event_tz).astimezone(timezone.utc)
    configured_reveal = event.wishes_reveal_at or event.reveal_at
    if configured_reveal:
        if configured_reveal.tzinfo is None:
            configured_reveal = configured_reveal.replace(tzinfo=event_tz)
        configured_reveal = configured_reveal.astimezone(timezone.utc)
        return max(birthday_start, configured_reveal)
    return birthday_start


def _is_birthday_person(current_user: Any) -> bool:
    return getattr(current_user, "role", None) in ("bday_person", "birthday_person", "bday-person", "org_admin", "admin", "super_admin")


def require_organization_manager(user_id: UUID, organization_id: UUID) -> None:
    """Allow only this organization's admin, with a super-admin override."""
    if not organization_service.can_manage_organization(user_id, organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )


# --- Static/sub-resource routes MUST come before /{event_id} ---

@router.get("/my-birthday-event", response_model=Event)
async def get_my_birthday_event(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """Return the current published event for admins or the birthday person."""
    role = getattr(current_user, "role_slug", getattr(current_user, "role", "")) or ""
    
    if role not in ("org_admin", "super_admin", "super-admin", "superadmin", "admin", "bday_person", "birthday_person", "bday-person"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This page is only available to admins or the birthday person")

    # Fetch organizations the user belongs to
    org_query = supabase.from_('organization_members').select('organization_id').eq('user_id', str(current_user.id)).is_('deleted_at', 'null')
    if role in ("bday_person", "birthday_person", "bday-person"):
        org_query = org_query.eq('role', 'bday_person')
        
    org_resp = org_query.execute()
    
    if not org_resp.data:
        raise HTTPException(status_code=404, detail="No published event found")
        
    org_ids = [om['organization_id'] for om in org_resp.data]
    
    # Fetch events for these orgs
    events_resp = (
        supabase.from_('events')
        .select('id')
        .in_('organization_id', org_ids)
        .is_('deleted_at', 'null')
        .neq('status', 'archived')
        .order('event_date', desc=True)
        .order('created_at', desc=True)
        .limit(1)
        .execute()
    )
    
    if not events_resp.data:
        raise HTTPException(status_code=404, detail="No published event found")
        
    event_id_str = events_resp.data[0]['id']
    
    event = await event_service.get_event_by_id(supabase, UUID(event_id_str))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/my-birthday-event/reveal-status")
async def get_my_birthday_reveal_status(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Authoritative lock state for the birthday-person page and countdown."""
    if not _is_birthday_person(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This page is only available to the birthday person")
    event = await get_my_birthday_event(supabase, current_user)
    reveal_at = _reveal_time(event)
    org_settings = {}
    org_resp = supabase.from_('organizations').select('settings').eq('id', str(event.organization_id)).single().execute()
    if org_resp.data and org_resp.data.get('settings'):
        org_settings = org_resp.data['settings']
    return {"event": event, "reveal_at": reveal_at, "is_revealed": datetime.now(timezone.utc) >= reveal_at, "org_settings": org_settings}


@router.get("/my-wisher-access")
async def get_my_wisher_access(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Wishers lose their contribution portal when their celebration opens."""
    # Fetch organizations the user is a member of
    org_member_resp = supabase.from_('organization_members').select('organization_id').eq('user_id', str(current_user.id)).is_('deleted_at', 'null').execute()
    org_ids = [om['organization_id'] for om in org_member_resp.data] if org_member_resp.data else []
    
    event = None
    if org_ids:
        # Find the most recent event across these organizations
        events_resp = supabase.from_('events').select('id').in_('organization_id', org_ids).is_('deleted_at', 'null').order('event_date', desc=True).order('created_at', desc=True).limit(1).execute()
        if events_resp.data:
            event = await event_service.get_event_by_id(supabase, UUID(events_resp.data[0]['id']))

    revealed = bool(event and datetime.now(timezone.utc) >= _reveal_time(event))
    is_wisher = getattr(current_user, "role", None) == "wisher"
    allowed = not revealed if is_wisher else True
    
    return {"allowed": allowed, "is_revealed": revealed, "event": event}


@router.get("/{event_id}/reveal-status")
async def get_event_reveal_status(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client)
) -> Any:
    """Returns whether the birthday reveal time has passed. Frontend uses this for countdown."""
    event = await event_service.get_event_by_id(supabase, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    now = datetime.now(timezone.utc)
    reveal_at = event.reveal_at
    # Normalize reveal_at to aware datetime if it's naive
    if reveal_at and reveal_at.tzinfo is None:
        reveal_at = reveal_at.replace(tzinfo=timezone.utc)
    return {
        "reveal_at": reveal_at,
        "is_revealed": reveal_at is None or reveal_at <= now
    }


@router.post("/", response_model=Event, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    require_organization_manager(current_user.id, event_in.organization_id)
    event_in.created_by = current_user.id
    # A birthday person can only receive the celebration from published events.
    event_in.status = "published"
    event = await event_service.create_event(supabase, event_in)
    if not event:
        raise HTTPException(status_code=400, detail="Event creation failed")
    return event


@router.get("/{event_id}", response_model=Event)
async def get_event(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    event = await event_service.get_event_by_id(supabase, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    require_organization_manager(current_user.id, event.organization_id)
    return event


@router.put("/{event_id}", response_model=Event)
async def update_event(
    event_id: UUID,
    event_in: EventUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    existing_event = await event_service.get_event_by_id(supabase, event_id)
    if not existing_event:
        raise HTTPException(status_code=404, detail="Event not found")
    require_organization_manager(current_user.id, existing_event.organization_id)
    event = await event_service.update_event(supabase, event_id, event_in)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or update failed")
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> None:
    event = await event_service.get_event_by_id(supabase, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    require_organization_manager(current_user.id, event.organization_id)
    success = await event_service.delete_event(supabase, event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found or deletion failed")
