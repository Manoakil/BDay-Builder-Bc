from typing import List, Optional
from uuid import UUID
from datetime import datetime

from supabase import Client

from app.schemas.event import Event, EventCreate, EventUpdate, DownloadPackage, DownloadPackageCreate

async def create_event(supabase: Client, event_in: EventCreate) -> Optional[Event]:
    import secrets
    base_slug = event_in.slug
    current_slug = base_slug
    max_attempts = 5
    
    for attempt in range(max_attempts):
        try:
            event_in.slug = current_slug
            response = supabase.from_('events').insert(event_in.model_dump(mode='json')).execute()
            if response.data:
                return Event.model_validate(response.data[0])
            return None
        except Exception as e:
            error_str = str(e)
            if '23505' in error_str and 'events_slug_key' in error_str:
                if attempt < max_attempts - 1:
                    random_suffix = secrets.token_hex(3)
                    current_slug = f"{base_slug}-{random_suffix}"
                    continue
            print(f"Error creating event: {e}")
            return None
    return None

async def get_event_by_id(supabase: Client, event_id: UUID) -> Optional[Event]:
    try:
        response = supabase.from_('events').select('*').eq('id', str(event_id)).single().execute()
        if response.data:
            return Event.model_validate(response.data)
        return None
    except Exception as e:
        print(f"Error fetching event by ID: {e}")
        return None

async def update_event(supabase: Client, event_id: UUID, event_in: EventUpdate) -> Optional[Event]:
    try:
        response = supabase.from_('events').update(event_in.model_dump(mode='json', exclude_unset=True)).eq('id', str(event_id)).execute()
        if response.data:
            return Event.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error updating event: {e}")
        return None

async def delete_event(supabase: Client, event_id: UUID) -> bool:
    try:
        response = supabase.from_('events').delete().eq('id', str(event_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting event: {e}")
        return False

async def get_events_by_organization_id(supabase: Client, organization_id: UUID) -> List[Event]:
    try:
        response = supabase.from_('events').select('*').eq('organization_id', str(organization_id)).execute()
        if response.data:
            return [Event.model_validate(item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error fetching events by organization ID: {e}")
        return []

async def create_download_package(supabase: Client, package_in: DownloadPackageCreate) -> Optional[DownloadPackage]:
    try:
        response = supabase.from_('download_packages').insert(package_in.model_dump(mode='json')).execute()
        if response.data:
            return DownloadPackage.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error creating download package: {e}")
        return None

async def get_download_packages_by_event(supabase: Client, event_id: UUID) -> List[DownloadPackage]:
    try:
        response = supabase.from_('download_packages').select('*').eq('event_id', str(event_id)).execute()
        if response.data:
            return [DownloadPackage.model_validate(item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error fetching download packages: {e}")
        return []
