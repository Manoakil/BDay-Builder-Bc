from typing import List, Optional
from uuid import UUID
import psycopg2
from psycopg2.extras import RealDictCursor

from supabase import Client

from app.schemas.timeline import Timeline, TimelineCreate, TimelineUpdate
from app.config import settings


def _connection():
    """Create a database connection"""
    return psycopg2.connect(settings.DATABASE_URL.strip('"'))


def _timeline_from_row(row) -> Timeline:
    data = dict(row)
    metadata = data.pop('file_metadata', None) or {}
    data['media_url'] = metadata.get('public_url')
    return Timeline.model_validate(data)


def _resolve_creator_names(supabase: Client, user_ids: list) -> dict:
    name_map = {}
    cleaned_ids = list({str(uid) for uid in user_ids if uid})
    if not cleaned_ids:
        return name_map
    try:
        profs_resp = supabase.from_('profiles').select('id, full_name, display_name').in_('id', cleaned_ids).execute()
        for p in (profs_resp.data or []):
            name = p.get('full_name') or p.get('display_name')
            if name and str(name).strip():
                name_map[str(p['id'])] = str(name).strip()

        wishes_resp = supabase.from_('wishes').select('user_id, wisher_name').in_('user_id', cleaned_ids).execute()
        for w in (wishes_resp.data or []):
            w_name = w.get('wisher_name')
            uid = str(w.get('user_id')) if w.get('user_id') else None
            if uid and w_name and str(w_name).strip():
                name_map[uid] = str(w_name).strip()
    except Exception as ex:
        print(f"Error resolving creator names for timeline: {ex}")
    return name_map


async def create_timeline_entry(supabase: Client, timeline_in: TimelineCreate) -> Optional[Timeline]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = timeline_in.model_dump(mode='json', exclude_none=True)
            for non_col in ('media_url', 'media_mime_type', 'wisher_name', 'created_by_name'):
                data.pop(non_col, None)
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            col_str = ', '.join(columns)
            
            cursor.execute(
                f"INSERT INTO timeline ({col_str}) VALUES ({placeholders}) RETURNING *",
                [data[c] for c in columns]
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return _timeline_from_row(row)
        return None
    except Exception as e:
        print(f"Error creating timeline entry: {e}")
        return None


async def get_timeline_entries_by_event_id(supabase: Client, event_id: UUID) -> List[Timeline]:
    try:
        resp = supabase.from_('timeline').select('*, files(metadata, mime_type)').eq('event_id', str(event_id)).is_('deleted_at', 'null').order('entry_date', desc=True).execute()
        rows = resp.data or []
        user_ids = [r.get('created_by') for r in rows if r.get('created_by')]
        name_map = _resolve_creator_names(supabase, user_ids)

        entries = []
        for row in rows:
            f = row.pop('files', None) or {}
            row['file_metadata'] = f.get('metadata')
            row['media_mime_type'] = f.get('mime_type')
            creator_id = str(row.get('created_by')) if row.get('created_by') else None
            author = name_map.get(creator_id) if creator_id else None
            row['wisher_name'] = author
            row['created_by_name'] = author
            entries.append(_timeline_from_row(row))
        return entries
    except Exception as e:
        print(f"Error fetching timeline entries by event ID: {e}")
        return []


async def get_timeline_entries_by_user_id(supabase: Client, user_id: UUID) -> List[Timeline]:
    """Get all timeline entries created by a specific user"""
    try:
        resp = supabase.from_('timeline').select('*, files(metadata, mime_type)').eq('created_by', str(user_id)).is_('deleted_at', 'null').order('entry_date', desc=True).execute()
        rows = resp.data or []
        name_map = _resolve_creator_names(supabase, [user_id])
        author = name_map.get(str(user_id))

        entries = []
        for row in rows:
            f = row.pop('files', None) or {}
            row['file_metadata'] = f.get('metadata')
            row['media_mime_type'] = f.get('mime_type')
            row['wisher_name'] = author
            row['created_by_name'] = author
            entries.append(_timeline_from_row(row))
        return entries
    except Exception as e:
        print(f"Error fetching timeline entries by user ID: {e}")
        return []


async def get_timeline_entry_by_id(supabase: Client, timeline_entry_id: UUID) -> Optional[Timeline]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM timeline WHERE id = %s AND deleted_at IS NULL",
                (str(timeline_entry_id),)
            )
            row = cursor.fetchone()
            if row:
                return Timeline.model_validate(dict(row))
        return None
    except Exception as e:
        print(f"Error fetching timeline entry by ID: {e}")
        return None


async def update_timeline_entry(supabase: Client, timeline_entry_id: UUID, timeline_in: TimelineUpdate) -> Optional[Timeline]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = timeline_in.model_dump(mode='json', exclude_unset=True, exclude_none=True)
            for non_col in ('media_url', 'media_mime_type', 'wisher_name', 'created_by_name'):
                data.pop(non_col, None)
            if not data:
                return await get_timeline_entry_by_id(supabase, timeline_entry_id)
            
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            values = list(data.values())
            values.append(str(timeline_entry_id))
            
            cursor.execute(
                f"UPDATE timeline SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING *",
                values
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return Timeline.model_validate(dict(row))
        return None
    except Exception as e:
        print(f"Error updating timeline entry: {e}")
        return None


async def delete_timeline_entry(supabase: Client, timeline_entry_id: UUID) -> bool:
    try:
        with _connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE timeline SET deleted_at = NOW() WHERE id = %s RETURNING id",
                (str(timeline_entry_id),)
            )
            deleted = cursor.fetchone() is not None
            connection.commit()
            return deleted
    except Exception as e:
        print(f"Error deleting timeline entry: {e}")
        return False
