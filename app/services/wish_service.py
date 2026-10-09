import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extras import Json
from typing import List, Optional
from uuid import UUID

from supabase import Client

from app.schemas.wish import Wish, WishCreate, WishUpdate, Comment, CommentCreate, CommentUpdate, Reaction, ReactionCreate
from app.config import settings


def _connection():
    """Create a database connection"""
    return psycopg2.connect(settings.DATABASE_URL.strip('"'))


def _sql_value(value):
    """Adapt JSON fields explicitly; psycopg2 cannot insert a raw dict."""
    return Json(value) if isinstance(value, (dict, list)) else value


def _wish_from_row(row) -> Wish:
    data = dict(row)
    metadata = data.pop('file_metadata', None) or {}
    data['media_url'] = metadata.get('public_url')
    return Wish.model_validate(data)


async def create_wish(supabase: Client, wish_in: WishCreate) -> Optional[Wish]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = wish_in.model_dump(mode='json', exclude_none=True)
            # Remove None values that shouldn't be inserted
            data = {k: v for k, v in data.items() if v is not None}
            
            # Build INSERT query dynamically
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            col_str = ', '.join(columns)
            
            cursor.execute(
                f"INSERT INTO wishes ({col_str}) VALUES ({placeholders}) RETURNING *",
                [_sql_value(data[c]) for c in columns]
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return _wish_from_row(row)
        return None
    except Exception as e:
        print(f"Error creating wish: {e}")
        return None


async def get_approved_wishes_by_event_id(supabase: Client, event_id: UUID) -> List[Wish]:
    try:
        resp = supabase.from_('wishes').select('*, files(metadata, mime_type)').eq('event_id', str(event_id)).in_('status', ['approved', 'pending']).neq('visibility', 'secret').is_('deleted_at', 'null').order('created_at').execute()
        wishes = []
        for row in (resp.data or []):
            f = row.pop('files', None) or {}
            row['file_metadata'] = f.get('metadata')
            row['media_mime_type'] = f.get('mime_type')
            wishes.append(_wish_from_row(row))
        return wishes
    except Exception as e:
        print(f"Error fetching approved wishes: {e}")
        return []


async def get_secret_wishes_by_event_id(supabase: Client, event_id: UUID) -> List[Wish]:
    try:
        resp = supabase.from_('wishes').select('*, files(metadata, mime_type)').eq('event_id', str(event_id)).in_('status', ['approved', 'pending']).eq('visibility', 'secret').is_('deleted_at', 'null').order('created_at').execute()
        wishes = []
        for row in (resp.data or []):
            f = row.pop('files', None) or {}
            row['file_metadata'] = f.get('metadata')
            row['media_mime_type'] = f.get('mime_type')
            wishes.append(_wish_from_row(row))
        return wishes
    except Exception as e:
        print(f"Error fetching secret wishes: {e}")
        return []


async def get_wishes_by_event_id(supabase: Client, event_id: UUID) -> List[Wish]:
    try:
        resp = supabase.from_('wishes').select('*, files(metadata, mime_type)').eq('event_id', str(event_id)).is_('deleted_at', 'null').order('created_at', desc=True).execute()
        wishes = []
        for row in (resp.data or []):
            f = row.pop('files', None) or {}
            row['file_metadata'] = f.get('metadata')
            row['media_mime_type'] = f.get('mime_type')
            wishes.append(_wish_from_row(row))
        return wishes
    except Exception as e:
        print(f"Error fetching wishes by event ID: {e}")
        return []


async def get_wishes_by_user_id(supabase: Client, user_id: UUID) -> List[Wish]:
    """Get all wishes created by a specific user"""
    try:
        resp = supabase.from_('wishes').select('*, files(metadata, mime_type)').eq('user_id', str(user_id)).is_('deleted_at', 'null').order('created_at', desc=True).execute()
        wishes = []
        for row in (resp.data or []):
            f = row.pop('files', None) or {}
            row['file_metadata'] = f.get('metadata')
            row['media_mime_type'] = f.get('mime_type')
            wishes.append(_wish_from_row(row))
        return wishes
    except Exception as e:
        print(f"Error fetching wishes by user ID: {e}")
        return []


async def get_wish_by_id(supabase: Client, wish_id: UUID) -> Optional[Wish]:
    try:
        resp = supabase.from_('wishes').select('*, files(metadata, mime_type)').eq('id', str(wish_id)).is_('deleted_at', 'null').maybe_single().execute()
        if resp.data:
            row = resp.data
            f = row.pop('files', None) or {}
            row['file_metadata'] = f.get('metadata')
            row['media_mime_type'] = f.get('mime_type')
            return _wish_from_row(row)
        return None
    except Exception as e:
        print(f"Error fetching wish by ID: {e}")
        return None


async def update_wish(supabase: Client, wish_id: UUID, wish_in: WishUpdate) -> Optional[Wish]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = wish_in.model_dump(mode='json', exclude_unset=True, exclude_none=True)
            if not data:
                return await get_wish_by_id(supabase, wish_id)
            
            # Build UPDATE query dynamically
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            values = list(data.values())
            values.append(str(wish_id))
            
            cursor.execute(
                f"UPDATE wishes SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING *",
                values
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return Wish.model_validate(dict(row))
        return None
    except Exception as e:
        print(f"Error updating wish: {e}")
        return None


async def delete_wish(supabase: Client, wish_id: UUID) -> bool:
    try:
        with _connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE wishes SET deleted_at = NOW() WHERE id = %s RETURNING id",
                (str(wish_id),)
            )
            deleted = cursor.fetchone() is not None
            connection.commit()
            return deleted
    except Exception as e:
        print(f"Error deleting wish: {e}")
        return False


async def add_comment(supabase: Client, comment_in: CommentCreate) -> Optional[Comment]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = comment_in.model_dump(mode='json', exclude_none=True)
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            col_str = ', '.join(columns)
            
            cursor.execute(
                f"INSERT INTO comments ({col_str}) VALUES ({placeholders}) RETURNING *",
                [_sql_value(data[c]) for c in columns]
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return Comment.model_validate(dict(row))
        return None
    except Exception as e:
        print(f"Error adding comment: {e}")
        return None


async def add_reaction(supabase: Client, reaction_in: ReactionCreate) -> Optional[Reaction]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = reaction_in.model_dump(mode='json', exclude_none=True)
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            col_str = ', '.join(columns)
            
            cursor.execute(
                f"INSERT INTO reactions ({col_str}) VALUES ({placeholders}) RETURNING *",
                [_sql_value(data[c]) for c in columns]
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return Reaction.model_validate(dict(row))
        return None
    except Exception as e:
        print(f"Error adding reaction: {e}")
        return None
