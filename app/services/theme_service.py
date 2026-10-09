from typing import List, Optional
from uuid import UUID

from supabase import Client

from app.schemas.theme import Theme, ThemeCreate, ThemeUpdate, OrganizationTheme, OrganizationThemeCreate, OrganizationThemeUpdate

async def get_all_themes(supabase: Client) -> List[Theme]:
    try:
        response = supabase.from_('themes').select('*').eq('is_public', True).execute()
        if response.data:
            return [Theme.model_validate(item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error fetching all themes: {e}")
        return []

async def get_theme_by_id(supabase: Client, theme_id: UUID) -> Optional[Theme]:
    try:
        response = supabase.from_('themes').select('*').eq('id', str(theme_id)).single().execute()
        if response.data:
            return Theme.model_validate(response.data)
        return None
    except Exception as e:
        print(f"Error fetching theme by ID: {e}")
        return None

async def assign_theme_to_organization(supabase: Client, org_theme_in: OrganizationThemeCreate) -> Optional[OrganizationTheme]:
    try:
        response = supabase.from_('organization_themes').insert(org_theme_in.model_dump(mode='json')).execute()
        if response.data:
            return OrganizationTheme.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error assigning theme to organization: {e}")
        return None

async def set_active_theme_for_organization(supabase: Client, organization_id: UUID, theme_id: UUID) -> Optional[OrganizationTheme]:
    try:
        # Deactivate all current themes for the organization
        supabase.from_('organization_themes').update({'is_active': False}).eq('organization_id', str(organization_id)).execute()
        
        # Set the specified theme as active
        response = supabase.from_('organization_themes').update({'is_active': True}).eq('organization_id', str(organization_id)).eq('theme_id', str(theme_id)).execute()
        
        if response.data:
            return OrganizationTheme.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error setting active theme for organization: {e}")
        return None
