import uuid
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from supabase import Client, create_client

from app.schemas.file import File, FileCreate
from app.schemas.common import StorageBucket
from app.config import settings


# These are the only buckets whose files are deliberately rendered in the
# celebration UI. They need browser-readable URLs for the birthday person.
PUBLIC_MEDIA_BUCKETS = {
    StorageBucket.wishes.value,
    StorageBucket.timeline.value,
    StorageBucket.voice_notes.value,
    StorageBucket.gallery.value,
    StorageBucket.avatars.value,
    StorageBucket.logos.value,
    StorageBucket.events.value,
}


def _upload_to_bucket(supabase: Client, bucket: str, path: str, content: bytes, content_type: Optional[str]) -> None:
    """Upload and provision an approved public media bucket when missing."""
    storage = supabase.storage
    try:
        storage.from_(bucket).upload(path, content, {"contentType": content_type})
    except Exception as exc:
        if "bucket not found" not in str(exc).lower() or bucket not in PUBLIC_MEDIA_BUCKETS:
            raise
        try:
            storage.create_bucket(bucket, options={"public": True})
        except Exception as create_exc:
            # A concurrent first upload can create the same bucket.
            if "already exists" not in str(create_exc).lower():
                raise
        storage.from_(bucket).upload(path, content, {"contentType": content_type})

async def upload_file(
    supabase: Client,
    bucket_name: StorageBucket,
    file: UploadFile,
    user_id: UUID,
    organization_id: Optional[UUID] = None,
    event_id: Optional[UUID] = None
) -> Optional[File]:
    try:
        import re
        # This route already requires an authenticated user. Use the
        # server-only storage key here, rather than weakening Storage RLS for
        # the public anon key used by browsers.
        upload_client = (
            create_client(settings.SUPABASE_URL, settings.SUPABASE_STORAGE_SERVICE_ROLE_KEY)
            if settings.SUPABASE_STORAGE_SERVICE_ROLE_KEY else supabase
        )
        file_content = await file.read()
        safe_filename = re.sub(r'[^a-zA-Z0-9.\-_]', '_', file.filename) if file.filename else "file"
        file_path = f"{user_id}/{uuid.uuid4()}-{safe_filename}" # Unique path for each file

        _upload_to_bucket(upload_client, bucket_name.value, file_path, file_content, file.content_type)
        
        if file_content is not None:
            # Get public URL if bucket is public, otherwise generate signed URL
            # For simplicity, assuming most uploaded files will eventually be accessible
            public_url = upload_client.storage.from_(bucket_name.value).get_public_url(file_path)

            file_data = FileCreate(
                organization_id=organization_id,
                event_id=event_id,
                bucket=bucket_name,
                path=file_path,
                filename=file.filename,
                original_name=file.filename,
                mime_type=file.content_type,
                size_bytes=file.size,
                file_type=file.content_type.split('/')[0] if file.content_type else 'other',
                is_public=bucket_name.value in PUBLIC_MEDIA_BUCKETS,
                uploaded_by=user_id,
                metadata={"public_url": public_url}
            )
            # Save file metadata to the 'files' table
            db_response = upload_client.from_('files').insert(file_data.model_dump(mode='json')).execute()
            if db_response.data:
                return File.model_validate(db_response.data[0])
        return None
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None
