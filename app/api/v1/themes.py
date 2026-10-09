from typing import List, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.theme import Theme, ThemeCreate, ThemeUpdate, OrganizationTheme, OrganizationThemeCreate, OrganizationThemeUpdate
from app.services import theme_service
from app.dependencies import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Theme])
async def get_all_themes(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user) # Optional auth
) -> List[Theme]:
    themes = await theme_service.get_all_themes(supabase)
    return themes

@router.get("/{theme_id}", response_model=Theme)
async def get_theme_by_id(
    theme_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user) # Optional auth
) -> Any:
    theme = await theme_service.get_theme_by_id(supabase, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme

@router.post("/{organization_id}/assign", response_model=OrganizationTheme, status_code=status.HTTP_201_CREATED)
async def assign_theme_to_organization(
    organization_id: UUID,
    org_theme_in: OrganizationThemeCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    org_theme_in.organization_id = organization_id
    # TODO: Add RBAC for org admin/owner
    org_theme = await theme_service.assign_theme_to_organization(supabase, org_theme_in)
    if not org_theme:
        raise HTTPException(status_code=400, detail="Theme assignment failed")
    return org_theme

@router.put("/{organization_id}/active-theme", response_model=OrganizationTheme)
async def set_active_organization_theme(
    organization_id: UUID,
    theme_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    # TODO: Add RBAC for org admin/owner
    active_theme = await theme_service.set_active_theme_for_organization(supabase, organization_id, theme_id)
    if not active_theme:
        raise HTTPException(status_code=400, detail="Setting active theme failed")
    return active_theme
