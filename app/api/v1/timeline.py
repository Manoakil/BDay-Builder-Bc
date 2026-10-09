from typing import List, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.timeline import Timeline, TimelineCreate, TimelineUpdate
from app.services import timeline_service
from app.dependencies import get_current_user

router = APIRouter()


# --- My timeline entries endpoint (for wisher dashboard) ---
@router.get("/my", response_model=List[Timeline])
async def get_my_timeline_entries(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> List[Timeline]:
    """Get all timeline entries created by the current user."""
    entries = await timeline_service.get_timeline_entries_by_user_id(supabase, current_user.id)
    return entries


@router.post("/", response_model=Timeline, status_code=status.HTTP_201_CREATED)
async def create_timeline_entry(
    timeline_in: TimelineCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    timeline_in.created_by = current_user.id
    # Auto-assign event_id from user's organization if not provided
    if not timeline_in.event_id:
        import psycopg2
        from app.config import settings
        with psycopg2.connect(settings.DATABASE_URL.strip('"')) as conn, conn.cursor() as cursor:
            # Get user's org
            cursor.execute(
                """SELECT om.organization_id FROM organization_members om
                   WHERE om.user_id = %s AND om.deleted_at IS NULL
                   ORDER BY om.created_at LIMIT 1""",
                (str(current_user.id),)
            )
            org_row = cursor.fetchone()
            if org_row:
                org_id = org_row[0]
                # Timeline entries may be added while the event is still a draft.
                cursor.execute(
                    """SELECT id FROM events 
                       WHERE organization_id = %s AND deleted_at IS NULL
                       ORDER BY event_date DESC, created_at DESC LIMIT 1""",
                    (str(org_id),)
                )
                event_row = cursor.fetchone()
                if event_row:
                    timeline_in.event_id = UUID(event_row[0])
                else:
                    cursor.execute(
                        """INSERT INTO events
                           (organization_id, title, slug, event_type, event_date,
                            status, visibility, created_by, published_at, reveal_at)
                           VALUES (%s, %s, %s, 'birthday', CURRENT_DATE + interval '7 days',
                                   'published', 'private', %s, NOW(), NOW() + interval '7 days')
                           RETURNING id""",
                        (str(org_id), "Birthday Celebration", f"birthday-{str(org_id)[:8]}", str(current_user.id))
                    )
                    timeline_in.event_id = UUID(str(cursor.fetchone()[0]))
    if not timeline_in.event_id:
        raise HTTPException(status_code=400, detail="No organization is assigned to this account. Join an event before adding a memory.")
    timeline_entry = await timeline_service.create_timeline_entry(supabase, timeline_in)
    if not timeline_entry:
        raise HTTPException(status_code=400, detail="Timeline entry creation failed")
    return timeline_entry


@router.get("/{event_id}", response_model=List[Timeline])
async def get_timeline_for_event(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user) # Optional auth
) -> List[Timeline]:
    # TODO: Implement RLS checks
    timeline_entries = await timeline_service.get_timeline_entries_by_event_id(supabase, event_id)
    
    return timeline_entries


@router.put("/{timeline_entry_id}", response_model=Timeline)
async def update_timeline_entry(
    timeline_entry_id: UUID,
    timeline_in: TimelineUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    # TODO: Add RLS/RBAC check
    timeline_entry = await timeline_service.update_timeline_entry(supabase, timeline_entry_id, timeline_in)
    if not timeline_entry:
        raise HTTPException(status_code=404, detail="Timeline entry not found or update failed")
    return timeline_entry


@router.delete("/{timeline_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timeline_entry(
    timeline_entry_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> None:
    # TODO: Add RLS/RBAC check
    success = await timeline_service.delete_timeline_entry(supabase, timeline_entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Timeline entry not found or deletion failed")
