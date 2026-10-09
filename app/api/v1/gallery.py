from typing import List, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.gallery import Gallery, GalleryCreate, GalleryUpdate
from app.services import gallery_service
from app.dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=Gallery, status_code=status.HTTP_201_CREATED)
async def create_gallery_item(
    gallery_in: GalleryCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    gallery_in.created_by = current_user.id
    gallery_item = await gallery_service.create_gallery_item(supabase, gallery_in)
    if not gallery_item:
        raise HTTPException(status_code=400, detail="Gallery item creation failed")
    return gallery_item

@router.get("/{event_id}", response_model=List[Gallery])
async def get_gallery_for_event(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user) # Optional auth
) -> List[Gallery]:
    # TODO: Implement RLS checks
    gallery_items = await gallery_service.get_gallery_items_by_event_id(supabase, event_id)
    return gallery_items

@router.put("/{gallery_item_id}", response_model=Gallery)
async def update_gallery_item(
    gallery_item_id: UUID,
    gallery_in: GalleryUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    # TODO: Add RLS/RBAC check
    gallery_item = await gallery_service.update_gallery_item(supabase, gallery_item_id, gallery_in)
    if not gallery_item:
        raise HTTPException(status_code=404, detail="Gallery item not found or update failed")
    return gallery_item

@router.delete("/{gallery_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gallery_item(
    gallery_item_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> None:
    # TODO: Add RLS/RBAC check
    success = await gallery_service.delete_gallery_item(supabase, gallery_item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Gallery item not found or deletion failed")
