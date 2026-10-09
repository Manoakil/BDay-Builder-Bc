from typing import List, Any
from uuid import UUID
from datetime import datetime, timezone
from app.api.v1.events import _reveal_time

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.wish import Wish, WishCreate, WishUpdate, Comment, CommentCreate, CommentUpdate, Reaction, ReactionCreate
from app.schemas.common import WishStatus
from app.services import wish_service
from app.services import organization_service
from app.services import event_service
from app.dependencies import get_current_user

router = APIRouter()


# --- Feed endpoint MUST be before /{event_id} to avoid UUID routing conflict ---
@router.get("/feed/{event_id}")
async def get_wish_feed(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client)
) -> Any:
    """Returns approved wishes split into video wishes and text wish wall,
    only after reveal_at time has passed."""
    event_resp = supabase.from_('events').select('reveal_at').eq('id', str(event_id)).single().execute()
    if not event_resp.data:
        raise HTTPException(status_code=404, detail="Event not found")
    reveal_at_str = event_resp.data.get('reveal_at')
    if reveal_at_str:
        # Supabase returns ISO 8601 — handle both +00:00 and Z suffixes
        reveal_at = datetime.fromisoformat(reveal_at_str.replace('Z', '+00:00'))
        if reveal_at > datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Wishes are not revealed yet")
    all_wishes = await wish_service.get_approved_wishes_by_event_id(supabase, event_id)
    return {
        "video_wishes": [w for w in all_wishes if w.wish_type in ('video', 'voice')],
        "wish_wall": [w for w in all_wishes if w.wish_type not in ('video', 'voice')]
    }


# --- My wishes endpoint (for wisher dashboard) ---
@router.get("/my", response_model=List[Wish])
async def get_my_wishes(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> List[Wish]:
    """Get all wishes created by the current user."""
    wishes = await wish_service.get_wishes_by_user_id(supabase, current_user.id)
    return wishes


@router.get("/birthday-person", response_model=List[Wish])
async def get_birthday_person_wishes(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> List[Wish]:
    """Return approved wishes only, after the server-side birthday reveal."""
    role = getattr(current_user, "role", "") or getattr(current_user, "role_slug", "") or ""
    if role not in ("org_admin", "super_admin", "admin", "bday_person", "birthday_person", "bday-person"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This page is only available to the birthday person or admins")
        
    org_query = supabase.from_('organization_members').select('organization_id').eq('user_id', str(current_user.id)).is_('deleted_at', 'null')
    if role in ("bday_person", "birthday_person", "bday-person"):
        org_query = org_query.eq('role', 'bday_person')
    org_resp = org_query.execute()
    
    org_ids = [m['organization_id'] for m in (org_resp.data or []) if 'organization_id' in m]
    
    if not org_ids:
        return []
        
    # 2. Get event
    events_resp = supabase.from_('events').select('id').in_('organization_id', org_ids).is_('deleted_at', 'null').neq('status', 'archived').order('event_date', desc=True).order('created_at', desc=True).limit(1).execute()
    if not events_resp.data:
        return []
        
    event_id = events_resp.data[0]['id']
    from app.services import event_service
    event = await event_service.get_event_by_id(supabase, UUID(str(event_id)))
    if not event or datetime.now(timezone.utc) < _reveal_time(event):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wishes are locked until the birthday celebration opens")
        
    wishes = await wish_service.get_approved_wishes_by_event_id(supabase, UUID(str(event_id)))
    
    return wishes


@router.get("/birthday-person-vault", response_model=List[Wish])
async def get_birthday_person_vault_wishes(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> List[Wish]:
    """Return secret vault wishes only, for the birthday person."""
    role = getattr(current_user, "role", "") or getattr(current_user, "role_slug", "") or ""
    if role not in ("org_admin", "super_admin", "admin", "bday_person", "birthday_person", "bday-person"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This page is only available to the birthday person or admins")
        
    org_query = supabase.from_('organization_members').select('organization_id').eq('user_id', str(current_user.id)).is_('deleted_at', 'null')
    if role in ("bday_person", "birthday_person", "bday-person"):
        org_query = org_query.eq('role', 'bday_person')
    org_resp = org_query.execute()
    
    org_ids = [m['organization_id'] for m in (org_resp.data or []) if 'organization_id' in m]
    
    if not org_ids:
        return []
        
    # 2. Get event
    events_resp = supabase.from_('events').select('id').in_('organization_id', org_ids).is_('deleted_at', 'null').neq('status', 'archived').order('event_date', desc=True).order('created_at', desc=True).limit(1).execute()
    if not events_resp.data:
        return []
        
    event_id = events_resp.data[0]['id']
    from app.services import event_service
    event = await event_service.get_event_by_id(supabase, UUID(str(event_id)))
    if not event or datetime.now(timezone.utc) < _reveal_time(event):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vault wishes are locked until the birthday celebration opens")
    return await wish_service.get_secret_wishes_by_event_id(supabase, UUID(str(event_id)))


@router.post("/{wish_id}/approve", response_model=Wish)
async def approve_wish(
    wish_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """Allow the owning org admin or any super admin to approve a wish."""
    # 1. Get the event_id for this wish
    wish_resp = supabase.from_('wishes').select('event_id').eq('id', str(wish_id)).single().execute()
    if not wish_resp.data:
        raise HTTPException(status_code=404, detail="Wish not found")
    event_id = wish_resp.data['event_id']

    # 2. Get the org_id for this event
    event_resp = supabase.from_('events').select('organization_id').eq('id', event_id).single().execute()
    if not event_resp.data:
        raise HTTPException(status_code=404, detail="Event not found")
    org_id = event_resp.data['organization_id']

    if not (
        organization_service.is_super_admin(current_user.id)
        or organization_service.is_org_admin(current_user.id, UUID(org_id))
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only org admin can approve wishes")

    wish = await wish_service.update_wish(supabase, wish_id, WishUpdate(status=WishStatus.approved))
    if not wish:
        raise HTTPException(status_code=400, detail="Approval failed")
    return wish


@router.patch("/{wish_id}", response_model=Wish)
async def edit_own_wish(
    wish_id: UUID,
    wish_in: WishUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """Only the wisher who created the wish can edit it. Status cannot be changed by wisher."""
    wish_resp = supabase.from_('wishes').select('user_id').eq('id', str(wish_id)).single().execute()
    if not wish_resp.data or str(wish_resp.data['user_id']) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own wish")
    wish_in.status = None  # Wishers cannot change approval status
    wish = await wish_service.update_wish(supabase, wish_id, wish_in)
    if not wish:
        raise HTTPException(status_code=404, detail="Wish not found or update failed")
    return wish


@router.delete("/{wish_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wish_endpoint(
    wish_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> None:
    """The wisher who created it, or the org admin can delete a wish."""
    wish_resp = supabase.from_('wishes').select('user_id, event_id').eq('id', str(wish_id)).single().execute()
    if not wish_resp.data:
        raise HTTPException(status_code=404, detail="Wish not found")
        
    event_resp = supabase.from_('events').select('organization_id').eq('id', wish_resp.data['event_id']).single().execute()
    is_admin = False
    if event_resp.data:
        is_admin = organization_service.can_manage_organization(current_user.id, UUID(event_resp.data['organization_id']))

    if str(wish_resp.data['user_id']) != str(current_user.id) and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own wish")
        
    success = await wish_service.delete_wish(supabase, wish_id)
    if not success:
        raise HTTPException(status_code=404, detail="Wish not found or deletion failed")


@router.post("/", response_model=Wish, status_code=status.HTTP_201_CREATED)
async def create_wish(
    wish_in: WishCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    if current_user:
        wish_in.user_id = current_user.id
        # Auto-assign event_id from user's organization if not provided
        if not wish_in.event_id:
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
                    # Use an existing event regardless of its publishing state.
                    # A wisher must be able to contribute before the reveal.
                    cursor.execute(
                        """SELECT id FROM events 
                           WHERE organization_id = %s AND deleted_at IS NULL
                           ORDER BY event_date DESC, created_at DESC LIMIT 1""",
                        (str(org_id),)
                    )
                    event_row = cursor.fetchone()
                    if event_row:
                        wish_in.event_id = UUID(event_row[0])
                    else:
                        # Some older organizations have members but no event.
                        # Create one safe, immediately usable birthday event so
                        # wishing never fails on a missing event_id.
                        cursor.execute(
                            """INSERT INTO events
                               (organization_id, title, slug, event_type, event_date,
                                status, visibility, created_by, published_at, reveal_at)
                               VALUES (%s, %s, %s, 'birthday', CURRENT_DATE + interval '7 days',
                                       'published', 'private', %s, NOW(), NOW() + interval '7 days')
                               RETURNING id""",
                            (str(org_id), "Birthday Celebration", f"birthday-{str(org_id)[:8]}", str(current_user.id))
                        )
                        wish_in.event_id = UUID(str(cursor.fetchone()[0]))
            if not wish_in.event_id:
                raise HTTPException(status_code=400, detail="No organization is assigned to this account. Join an event before sending a wish.")
    event = await event_service.get_event_by_id(supabase, wish_in.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    is_manager = organization_service.can_manage_organization(current_user.id, event.organization_id)
    if getattr(current_user, "role", None) in ("bday_person", "birthday_person", "bday-person"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The birthday person cannot add wishes to their own celebration")
    # The celebration is read-only after it opens. The coordinator keeps access
    # to correct event content if necessary.
    if datetime.now(timezone.utc) >= _reveal_time(event) and not is_manager:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wishes close when the birthday celebration opens")
    is_secret = wish_in.is_anonymous or str(wish_in.visibility) in ("WishVisibility.secret", "secret")
    if is_secret and not is_manager:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the organization admin can send secret or vault wishes")
    # Wishes should be waiting for the birthday person when the celebration
    # reveals; no hidden pending state is required for this workflow.
    wish_in.status = WishStatus.approved
    wish = await wish_service.create_wish(supabase, wish_in)
    if not wish:
        raise HTTPException(status_code=400, detail="Wish creation failed")
    return wish


@router.get("/{event_id}", response_model=List[Wish])
async def get_wishes_for_event(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> List[Wish]:
    wishes = await wish_service.get_wishes_by_event_id(supabase, event_id)
    return wishes


@router.post("/{wish_id}/comments", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def add_comment_to_wish(
    wish_id: UUID,
    comment_in: CommentCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    comment_in.wish_id = wish_id
    if current_user:
        comment_in.user_id = current_user.id
    comment = await wish_service.add_comment(supabase, comment_in)
    if not comment:
        raise HTTPException(status_code=400, detail="Comment creation failed")
    return comment


@router.post("/{wish_id}/reactions", response_model=Reaction, status_code=status.HTTP_201_CREATED)
async def add_reaction_to_wish(
    wish_id: UUID,
    reaction_in: ReactionCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    reaction_in.wish_id = wish_id
    if current_user:
        reaction_in.user_id = current_user.id
    reaction = await wish_service.add_reaction(supabase, reaction_in)
    if not reaction:
        raise HTTPException(status_code=400, detail="Reaction failed or already exists")
    return reaction
