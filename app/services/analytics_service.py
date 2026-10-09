from typing import Optional
from uuid import UUID

from supabase import Client

from app.schemas.analytics import EventAnalyticsSummary, PlatformMetrics, OrgMetrics

async def get_event_analytics_summary(supabase: Client, event_id: UUID) -> Optional[EventAnalyticsSummary]:
    try:
        # Call the PostgreSQL function get_event_analytics
        response = supabase.rpc('get_event_analytics', {'event_id': str(event_id)}).execute()
        
        if response.data:
            summary_data = response.data[0]
            return EventAnalyticsSummary(
                total_visitors=summary_data.get('total_visitors', 0),
                total_views=summary_data.get('total_views', 0),
                total_wishes=summary_data.get('total_wishes', 0),
                approved_wishes=summary_data.get('approved_wishes', 0),
                pending_wishes=summary_data.get('pending_wishes', 0),
                total_vault_attempts=summary_data.get('total_vault_attempts', 0),
                vault_unlocks=summary_data.get('vault_unlocks', 0),
                total_shares=summary_data.get('total_shares', 0),
                top_countries=summary_data.get('top_countries', {})
            )
        return None
    except Exception as e:
        print(f"Error getting event analytics summary: {e}")
        return None

async def get_platform_metrics(supabase: Client) -> PlatformMetrics:
    try:
        # We can either make individual calls or an RPC. Individual calls via supabase python client:
        # To bypass RLS and get true totals for super_admin, the client should have service role.
        # But this function is only hit if user is a super admin, so even if regular client it might see all if RLS policies allow super admins.
        
        # 1. Total Orgs
        orgs_res = supabase.table('organizations').select('id', count='exact').execute()
        total_orgs = orgs_res.count if orgs_res.count is not None else 0
        
        # 2. Active Orgs
        active_orgs_res = supabase.table('organizations').select('id', count='exact').eq('status', 'active').execute()
        active_orgs = active_orgs_res.count if active_orgs_res.count is not None else 0
        
        # 3. Total Users (Profiles)
        users_res = supabase.table('profiles').select('id', count='exact').execute()
        total_users = users_res.count if users_res.count is not None else 0
        
        # 4. Total Events
        events_res = supabase.table('events').select('id', count='exact').execute()
        total_events = events_res.count if events_res.count is not None else 0

        # 5. Total Wishes
        wishes_res = supabase.table('wishes').select('id', count='exact').execute()
        total_wishes = wishes_res.count if wishes_res.count is not None else 0

        # 6. Total Media
        files_res = supabase.table('files').select('id', count='exact').execute()
        total_media = files_res.count if files_res.count is not None else 0
        
        return PlatformMetrics(
            total_organizations=total_orgs,
            active_organizations=active_orgs,
            total_users=total_users,
            total_events=total_events,
            total_wishes=total_wishes,
            total_media=total_media
        )
    except Exception as e:
        print(f"Error getting platform metrics: {e}")
        return PlatformMetrics(total_organizations=0, active_organizations=0, total_users=0, total_events=0, total_wishes=0, total_media=0)

async def get_org_metrics(supabase: Client, org_id: str) -> OrgMetrics:
    try:
        # Total users in org
        total_users_res = supabase.table('organization_members').select('id', count='exact').eq('organization_id', org_id).execute()
        total_users = total_users_res.count if total_users_res.count is not None else 0
        
        # Pending users in org (status is on profiles table)
        members_res = supabase.table('organization_members').select('user_id').eq('organization_id', org_id).execute()
        user_ids = [m['user_id'] for m in members_res.data] if members_res.data else []
        pending_users = 0
        if user_ids:
            pending_res = supabase.table('profiles').select('id', count='exact').in_('id', user_ids).eq('approval_status', 'pending').execute()
            pending_users = pending_res.count if pending_res.count is not None else 0
        
        # We need the event id to count wishes. Get active event for this org.
        event_res = supabase.table('events').select('id').eq('organization_id', org_id).limit(1).execute()
        total_wishes = 0
        pending_wishes = 0
        vault_enabled = False
        
        if event_res.data and len(event_res.data) > 0:
            event_id = event_res.data[0]['id']
            # Total wishes
            tw_res = supabase.table('wishes').select('id', count='exact').eq('event_id', event_id).execute()
            total_wishes = tw_res.count if tw_res.count is not None else 0
            
            # Pending wishes
            pw_res = supabase.table('wishes').select('id', count='exact').eq('event_id', event_id).eq('status', 'pending').execute()
            pending_wishes = pw_res.count if pw_res.count is not None else 0
            
            # Vault status
            vault_res = supabase.table('secret_vault').select('is_enabled').eq('event_id', event_id).execute()
            if vault_res.data and len(vault_res.data) > 0:
                vault_enabled = vault_res.data[0].get('is_enabled', False)
                
        return OrgMetrics(
            total_users=total_users,
            pending_users=pending_users,
            total_wishes=total_wishes,
            pending_wishes=pending_wishes,
            vault_enabled=vault_enabled
        )
    except Exception as e:
        print(f"Error getting org metrics: {e}")
        return OrgMetrics(total_users=0, pending_users=0, total_wishes=0, pending_wishes=0, vault_enabled=False)
