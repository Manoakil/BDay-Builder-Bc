from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from uuid import UUID
import os

from app.dependencies import get_optional_current_user
from app.database import get_supabase_client
from typing import Any
from supabase import Client
from app.schemas.event import Event
from app.services import event_service, organization_service
from app.services.offline_generator import build_offline_package

router = APIRouter()

@router.get("/{event_id}/offline-package")
async def download_offline_package(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_optional_current_user)
):
    """
    Generates and returns a complete standalone offline website ZIP 
    for the specified birthday event.
    """
    event = await event_service.get_event_by_id(supabase, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    try:
        # Build the package (returns path to ZIP file)
        zip_path = await build_offline_package(supabase, event, start_step="welcome")
        
        # Return as downloadable file
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"birthday-{event.slug or event.id}.zip"
        )
    except Exception as e:
        print(f"Error generating offline package: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate offline package: {str(e)}"
        )

@router.get("/{event_id}/vault-package")
async def download_vault_package(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_optional_current_user)
):
    """
    Generates and returns a dedicated standalone offline website ZIP
    for the secret vault wish of the specified birthday event.
    """
    event = await event_service.get_event_by_id(supabase, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    try:
        # Build the package starting directly at vault-wishes
        zip_path = await build_offline_package(supabase, event, start_step="vault-wishes")
        
        # Return as downloadable file
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"secret-vault-{event.slug or event.id}.zip"
        )
    except Exception as e:
        print(f"Error generating vault package: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate vault offline package: {str(e)}"
        )
