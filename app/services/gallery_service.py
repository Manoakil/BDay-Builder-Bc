from typing import List, Optional
from uuid import UUID

from supabase import Client

from app.schemas.gallery import Gallery, GalleryCreate, GalleryUpdate

import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import settings

def _connection():
    return psycopg2.connect(settings.DATABASE_URL.strip('"'))

def _gallery_from_row(row) -> Gallery:
    data = dict(row)
    metadata = data.pop('file_metadata', None) or {}
    data['media_url'] = metadata.get('public_url')
    return Gallery.model_validate(data)

async def create_gallery_item(supabase: Client, gallery_in: GalleryCreate) -> Optional[Gallery]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = gallery_in.model_dump(mode='json', exclude_none=True)
            # Do not insert dynamically populated fields
            data.pop('media_url', None)
            data.pop('media_mime_type', None)
            
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            col_str = ', '.join(columns)
            
            cursor.execute(
                f"INSERT INTO gallery ({col_str}) VALUES ({placeholders}) RETURNING *",
                [data[c] for c in columns]
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return _gallery_from_row(row)
        return None
    except Exception as e:
        print(f"Error creating gallery item: {e}")
        return None

async def get_gallery_items_by_event_id(supabase: Client, event_id: UUID) -> List[Gallery]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """SELECT g.*, f.metadata AS file_metadata, f.mime_type AS media_mime_type
                   FROM gallery g LEFT JOIN files f ON f.id = g.file_id
                   WHERE g.event_id = %s AND g.deleted_at IS NULL
                   ORDER BY g.sort_order""",
                (str(event_id),)
            )
            return [_gallery_from_row(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching gallery items by event ID: {e}")
        return []

async def update_gallery_item(supabase: Client, gallery_item_id: UUID, gallery_in: GalleryUpdate) -> Optional[Gallery]:
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            data = gallery_in.model_dump(mode='json', exclude_unset=True, exclude_none=True)
            data.pop('media_url', None)
            data.pop('media_mime_type', None)
            if not data:
                # Return current object
                cursor.execute(
                    """SELECT g.*, f.metadata AS file_metadata, f.mime_type AS media_mime_type
                       FROM gallery g LEFT JOIN files f ON f.id = g.file_id
                       WHERE g.id = %s AND g.deleted_at IS NULL""",
                    (str(gallery_item_id),)
                )
                row = cursor.fetchone()
                return _gallery_from_row(row) if row else None
            
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            values = list(data.values())
            values.append(str(gallery_item_id))
            
            cursor.execute(
                f"""UPDATE gallery SET {set_clause}, updated_at = NOW() 
                    WHERE id = %s RETURNING *""",
                values
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                # Need the joined fields to fully construct
                cursor.execute(
                    """SELECT g.*, f.metadata AS file_metadata, f.mime_type AS media_mime_type
                       FROM gallery g LEFT JOIN files f ON f.id = g.file_id
                       WHERE g.id = %s AND g.deleted_at IS NULL""",
                    (str(gallery_item_id),)
                )
                full_row = cursor.fetchone()
                return _gallery_from_row(full_row) if full_row else None
        return None
    except Exception as e:
        print(f"Error updating gallery item: {e}")
        return None

async def delete_gallery_item(supabase: Client, gallery_item_id: UUID) -> bool:
    try:
        with _connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE gallery SET deleted_at = NOW() WHERE id = %s RETURNING id",
                (str(gallery_item_id),)
            )
            deleted = cursor.fetchone() is not None
            connection.commit()
            return deleted
    except Exception as e:
        print(f"Error deleting gallery item: {e}")
        return False
