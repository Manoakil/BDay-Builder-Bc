from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import secrets
import psycopg2
from psycopg2.extras import RealDictCursor

from supabase import Client

from app.schemas.organization import (
    Organization, 
    OrganizationCreate, 
    OrganizationUpdate, 
    Invite, 
    InviteCreate, 
    OrganizationMember, 
    OrganizationMemberCreate, 
    OrganizationMemberUpdate
)
from app.schemas.common import MemberRole
from app.config import settings


def _connection():
    """Create a database connection"""
    return psycopg2.connect(settings.DATABASE_URL.strip('"'))


def get_user_role_slug(user_id: UUID) -> Optional[str]:
    """Get user's role slug from profiles"""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT r.slug FROM profiles p LEFT JOIN roles r ON r.id = p.role_id WHERE p.id = %s",
            (str(user_id),),
        )
        row = cursor.fetchone()
        return row[0] if row else None


# =============================================
# ORGANIZATION CRUD OPERATIONS
# =============================================

async def create_organization(supabase: Client, org_in: OrganizationCreate) -> Optional[Organization]:
    """Create organization using Supabase client"""
    try:
        org_data = org_in.model_dump(mode='json')
        org_data['secret_code'] = secrets.token_urlsafe(6).upper()
        response = supabase.from_('organizations').insert(org_data).execute()
        if response.data:
            new_org = Organization.model_validate(response.data[0])

            # Automatically make the creator an 'org_admin'
            member_data = OrganizationMemberCreate(
                organization_id=new_org.id,
                user_id=org_in.created_by,
                role=MemberRole.ORG_ADMIN,
                is_primary=True
            )
            await add_organization_member(supabase, member_data)

            return new_org
        return None
    except Exception as e:
        print(f"Error creating organization: {e}")
        return None


async def create_organization_from_db(org_in: OrganizationCreate) -> Optional[Organization]:
    """Create organization using direct database connection"""
    try:
        print("=" * 50)
        print("🔍 Starting organization creation...")
        print(f"👤 User ID: {org_in.created_by}")
        
        # Ensure user has a profile
        with _connection() as connection, connection.cursor() as cursor:
            # Check if profile exists
            cursor.execute(
                "SELECT id, email FROM profiles WHERE id = %s",
                (str(org_in.created_by),)
            )
            profile = cursor.fetchone()
            
            if not profile:
                print("❌ User does not have a profile. Creating one...")
                
                # Get email from auth.users
                cursor.execute(
                    "SELECT email FROM auth.users WHERE id = %s",
                    (str(org_in.created_by),)
                )
                auth_user = cursor.fetchone()
                
                if not auth_user:
                    print(f"❌ User {org_in.created_by} not found in auth.users")
                    return None
                
                email = auth_user[0]
                
                # Create profile
                cursor.execute(
                    """INSERT INTO profiles (id, full_name, display_name, email, approval_status, status, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, 'approved', 'active', %s, %s)""",
                        str(org_in.created_by),
                        'Super Admin',
                        'Super Admin',
                        email,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                
                connection.commit()
                print("✅ Profile created successfully")
            else:
                print(f"✅ Profile exists for user {org_in.created_by}")
        
        # Now create organization
        import json
        org_data = org_in.model_dump(mode="json")
        org_data["secret_code"] = secrets.token_urlsafe(6).upper()
        if "address" in org_data and isinstance(org_data["address"], dict):
            org_data["address"] = json.dumps(org_data["address"])
        print(f"📦 Org data: {org_data}")
        
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            print("📝 Inserting organization...")
            cursor.execute(
                """INSERT INTO organizations (name, slug, description, logo_url, cover_url, website, email, phone, address, created_by, secret_code, status)
                   VALUES (%(name)s, %(slug)s, %(description)s, %(logo_url)s, %(cover_url)s, %(website)s, %(email)s, %(phone)s, %(address)s, %(created_by)s, %(secret_code)s, 'active')
                   RETURNING *""",
                org_data,
            )
            result = cursor.fetchone()
            if not result:
                print("❌ No result from INSERT")
                return None
                
            print(f"✅ Organization inserted: {dict(result)}")
            organization = Organization.model_validate(dict(result))
            
            # Insert member as super_admin (with underscore)
            print(f"👤 Adding member as super_admin...")
            cursor.execute(
                """INSERT INTO organization_members (organization_id, user_id, role, is_primary, joined_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    str(organization.id),
                    str(org_in.created_by),
                    "super_admin",  # ✅ CORRECT: with underscore
                    True,
                    datetime.now().isoformat()
                ),
            )
            
            # Update profile with default organization
            print(f"📝 Updating profile...")
            cursor.execute(
                "UPDATE profiles SET default_organization_id = %s WHERE id = %s",
                (str(organization.id), str(org_in.created_by)),
            )
            
            connection.commit()
            print("✅ All changes committed!")
            
        return organization
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        print(f"Error Code: {e.pgcode}")
        print(f"Error Message: {e.pgerror}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"❌ Error creating organization from DB: {e}")
        import traceback
        traceback.print_exc()
        return None


async def get_organization_by_id(supabase: Client, org_id: UUID) -> Optional[Organization]:
    """Get organization by ID"""
    try:
        response = supabase.from_('organizations').select('*').eq('id', str(org_id)).single().execute()
        if response.data:
            return Organization.model_validate(response.data)
        return None
    except Exception as e:
        print(f"Error fetching organization by ID: {e}")
        return None


async def update_organization(supabase: Client, org_id: UUID, org_in: OrganizationUpdate) -> Optional[Organization]:
    """Update organization"""
    try:
        response = supabase.from_('organizations').update(org_in.model_dump(mode='json', exclude_unset=True)).eq('id', str(org_id)).execute()
        if response.data:
            return Organization.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error updating organization: {e}")
        return None


async def delete_organization(supabase: Client, org_id: UUID) -> bool:
    """Delete organization (soft delete)"""
    try:
        from datetime import datetime
        response = supabase.from_('organizations').update({'deleted_at': datetime.now().isoformat(), 'status': 'deleted'}).eq('id', str(org_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting organization: {e}")
        return False


async def get_all_organizations(supabase: Client) -> List[Organization]:
    """Get all organizations"""
    try:
        response = supabase.from_('organizations').select('*').is_('deleted_at', 'null').order('created_at').execute()
        if response.data:
            return [Organization.model_validate(item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error fetching all organizations: {e}")
        return []


async def get_all_organizations_from_db() -> List[Organization]:
    """Get all organizations from database (direct connection)"""
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM organizations WHERE deleted_at IS NULL ORDER BY created_at")
            return [Organization.model_validate(dict(row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching organizations: {e}")
        return []

async def get_all_global_members() -> List[dict]:
    """Get all members across all organizations for Super Admin"""
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    om.id as member_id, 
                    om.user_id, 
                    om.organization_id, 
                    om.role, 
                    p.full_name, 
                    p.email, 
                    o.name as organization_name,
                    p.approval_status,
                    p.created_at
                FROM organization_members om
                JOIN profiles p ON om.user_id = p.id
                JOIN organizations o ON om.organization_id = o.id
                WHERE om.deleted_at IS NULL
                ORDER BY p.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching global members: {e}")
        return []


async def get_organizations_by_user(supabase: Client, user_id: UUID) -> List[Organization]:
    """Get organizations by user ID"""
    try:
        memberships = supabase.from_('organization_members').select('organization_id').eq('user_id', str(user_id)).execute()
        org_ids = [m['organization_id'] for m in (memberships.data or []) if 'organization_id' in m]
        if not org_ids:
            return []
        response = supabase.from_('organizations').select('*').in_('id', org_ids).is_('deleted_at', 'null').execute()
        if response.data:
            return [Organization.model_validate(item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error fetching organizations by user: {e}")
        return []


async def regenerate_secret_code(supabase: Client, org_id: UUID) -> Optional[Organization]:
    """Regenerate organization secret code"""
    try:
        new_code = secrets.token_urlsafe(6).upper()
        response = supabase.from_('organizations').update({'secret_code': new_code, 'updated_at': datetime.now().isoformat()}).eq('id', str(org_id)).execute()
        if response.data:
            return Organization.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error regenerating secret code: {e}")
        return None


# =============================================
# ORGANIZATION MEMBERS OPERATIONS
# =============================================

async def add_organization_member(supabase: Client, member_in: OrganizationMemberCreate) -> Optional[OrganizationMember]:
    """Add a member to organization"""
    try:
        member_data = member_in.model_dump(mode='json')
        if 'role' in member_data and isinstance(member_data['role'], MemberRole):
            member_data['role'] = member_data['role'].value
        response = supabase.from_('organization_members').insert(member_data).execute()
        if response.data:
            return OrganizationMember.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error adding organization member: {e}")
        return None


async def update_organization_member(supabase: Client, member_id: UUID, member_in: OrganizationMemberUpdate) -> Optional[OrganizationMember]:
    """Update organization member"""
    try:
        member_data = member_in.model_dump(mode='json', exclude_unset=True)
        if 'role' in member_data and isinstance(member_data['role'], MemberRole):
            member_data['role'] = member_data['role'].value
        response = supabase.from_('organization_members').update(member_data).eq('id', str(member_id)).execute()
        if response.data:
            return OrganizationMember.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error updating organization member: {e}")
        return None


async def remove_organization_member(supabase: Client, member_id: UUID) -> bool:
    """Remove organization member"""
    try:
        response = supabase.from_('organization_members').delete().eq('id', str(member_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error removing organization member: {e}")
        return False


async def get_organization_members(supabase: Client, org_id: UUID) -> List[OrganizationMember]:
    """Get all members of an organization"""
    try:
        response = supabase.from_('organization_members').select('*').eq('organization_id', str(org_id)).execute()
        if response.data:
            return [OrganizationMember.model_validate(item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error fetching organization members: {e}")
        return []


async def get_org_members_with_profiles(org_id: UUID) -> List[dict]:
    """Fetch org members joined with profile info"""
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_STORAGE_SERVICE_ROLE_KEY)
        
        # We can't do a direct left join easily with REST API in one go if foreign keys aren't set up perfectly,
        # so we fetch members first and then fetch profiles separately.
        response = supabase.from_('organization_members').select('id, organization_id, user_id, role, joined_at, is_primary').eq('organization_id', str(org_id)).neq('role', 'super_admin').is_('deleted_at', 'null').order('joined_at').execute()
        
        if not response.data:
            return []
            
        user_ids = [row.get('user_id') for row in response.data if row.get('user_id')]
        profiles_dict = {}
        if user_ids:
            # Fetch profiles for these users
            prof_resp = supabase.from_('profiles').select('id, full_name, approval_status, status, date_of_birth, rejection_reason').in_('id', user_ids).execute()
            if prof_resp.data:
                for p in prof_resp.data:
                    profiles_dict[p['id']] = p

            # Fetch emails via Admin API
            try:
                for uid in user_ids:
                    if uid not in profiles_dict:
                        profiles_dict[uid] = {}
                    user_resp = supabase.auth.admin.get_user_by_id(uid)
                    if user_resp and user_resp.user:
                        profiles_dict[uid]['email'] = user_resp.user.email
            except Exception as e:
                print(f"Error fetching emails from auth admin: {e}")

        results = []
        for row in response.data:
            user_id = row.get("user_id")
            p = profiles_dict.get(user_id) or {}
            results.append({
                "id": row.get("id"),
                "organization_id": row.get("organization_id"),
                "user_id": user_id,
                "role": row.get("role"),
                "joined_at": row.get("joined_at"),
                "created_at": row.get("joined_at"), # Use joined_at as fallback for created_at
                "is_primary": row.get("is_primary"),
                "full_name": p.get("full_name"),
                "email": p.get("email"),
                "approval_status": p.get("approval_status"),
                "status": p.get("status"),
                "date_of_birth": p.get("date_of_birth"),
                "rejection_reason": p.get("rejection_reason")
            })
        return results
    except Exception as e:
        print(f"Error fetching org members with profiles: {e}")
        return []


def get_member_role(user_id: UUID, org_id: UUID) -> Optional[str]:
    """Get a user's role within a specific org"""
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_STORAGE_SERVICE_ROLE_KEY)
        resp = supabase.from_('organization_members').select('role').eq('user_id', str(user_id)).eq('organization_id', str(org_id)).is_('deleted_at', 'null').limit(1).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]['role']
        return None
    except Exception as e:
        print(f"Failed to check member role: {e}")
        return None


def is_super_admin(user_id: UUID) -> bool:
    """Check if the user is a super admin"""
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_STORAGE_SERVICE_ROLE_KEY)
        
        # Check org members
        org_resp = supabase.from_('organization_members').select('id').eq('user_id', str(user_id)).eq('role', 'super_admin').is_('deleted_at', 'null').limit(1).execute()
        if org_resp.data:
            return True
            
        # Check profile role
        profile_resp = supabase.from_('profiles').select('roles(slug)').eq('id', str(user_id)).limit(1).execute()
        if profile_resp.data and profile_resp.data[0].get('roles'):
            slug = profile_resp.data[0]['roles'].get('slug')
            if slug in ('super-admin', 'super_admin', 'superadmin'):
                return True
                
        return False
    except Exception as e:
        print(f"Failed to check super_admin status: {e}")
        return False


def is_org_admin(user_id: UUID, org_id: UUID) -> bool:
    """Check if the user is an org_admin of the given org"""
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_STORAGE_SERVICE_ROLE_KEY)
        resp = supabase.from_('organization_members').select('id').eq('user_id', str(user_id)).eq('organization_id', str(org_id)).eq('role', 'org_admin').is_('deleted_at', 'null').limit(1).execute()
        return bool(resp.data)
    except Exception as e:
        print(f"Failed to check org_admin status: {e}")
        return False


def can_manage_organization(user_id: UUID, org_id: UUID) -> bool:
    """Check management access for one organization only."""
    return is_super_admin(user_id) or is_org_admin(user_id, org_id)


def member_belongs_to_organization(member_id: UUID, org_id: UUID) -> bool:
    """Check that a membership record belongs to the organization in the URL."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT 1 FROM organization_members
               WHERE id = %s AND organization_id = %s AND deleted_at IS NULL""",
            (str(member_id), str(org_id)),
        )
        return cursor.fetchone() is not None


def registration_identity_exists(email: str) -> Optional[str]:
    """Return the duplicate signup field, if an account already exists."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM auth.users WHERE lower(email) = lower(%s)", (email,))
        if cursor.fetchone():
            return "email"
    return None


async def set_member_approval(
    user_id: UUID,
    org_id: UUID,
    approver_id: UUID,
    decision: str,
    rejection_reason: Optional[str] = None,
) -> Optional[dict]:
    """Approve or reject a member's access to an org"""
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            now = datetime.now().isoformat()
            if decision == 'approved':
                cursor.execute(
                    """UPDATE profiles SET approval_status = 'approved', approved_by = %s,
                           approved_at = %s, rejection_reason = NULL, status = 'active'
                       WHERE id = %s""",
                    (str(approver_id), now, str(user_id)),
                )
            else:
                cursor.execute(
                    """UPDATE profiles SET approval_status = 'rejected', approved_by = %s,
                           approved_at = %s, rejection_reason = %s, status = 'suspended'
                       WHERE id = %s""",
                    (str(approver_id), now, rejection_reason, str(user_id)),
                )
            connection.commit()

            cursor.execute(
                """SELECT om.id as member_id, om.organization_id, om.user_id,
                          org.name as organization_name,
                          p.full_name, p.email, p.approval_status,
                          om.role, p.rejection_reason
                   FROM organization_members om
                   JOIN organizations org ON org.id = om.organization_id
                   JOIN profiles p ON p.id = om.user_id
                   WHERE om.user_id = %s AND om.organization_id = %s AND om.deleted_at IS NULL""",
                (str(user_id), str(org_id)),
            )
            row = cursor.fetchone()
            connection.commit()
            if row:
                return dict(row)
        return None
    except Exception as e:
        print(f"Error setting member approval: {e}")
        return None


async def get_pending_org_admins() -> List[dict]:
    """Return org_admin memberships that are pending approval (for super admin)"""
    try:
        with _connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """SELECT om.id as member_id, om.organization_id, om.user_id,
                          org.name as organization_name, org.secret_code,
                          p.full_name, p.email, p.approval_status, p.rejection_reason,
                          om.created_at
                   FROM organization_members om
                   JOIN organizations org ON org.id = om.organization_id
                   JOIN profiles p ON p.id = om.user_id
                   WHERE om.role = 'org_admin' AND om.deleted_at IS NULL
                         AND (p.approval_status IS NULL OR p.approval_status = 'pending')
                   ORDER BY om.created_at ASC"""
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching pending org admins: {e}")
        return []

async def create_invite(supabase: Client, invite_in: InviteCreate) -> Optional[Invite]:
    """Create an invite"""
    try:
        token = secrets.token_urlsafe(32)
        expires_at = invite_in.expires_at or (datetime.now() + timedelta(days=7))

        invite_data = invite_in.model_dump(mode='json')
        invite_data['token'] = token
        invite_data['expires_at'] = expires_at.isoformat() if isinstance(expires_at, datetime) else expires_at
        
        response = supabase.from_('invites').insert(invite_data).execute()
        if response.data:
            return Invite.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error creating invite: {e}")
        return None


async def accept_invite(supabase: Client, token: str, user_id: UUID) -> Optional[OrganizationMember]:
    """Accept an invite"""
    try:
        # 1. Find the invite
        response = supabase.from_('invites').select('*').eq('token', token).single().execute()
        invite = response.data

        if not invite or invite['status'] != 'pending' or datetime.fromisoformat(invite['expires_at']) < datetime.now():
            return None

        # 2. Add user to organization members
        member_data = OrganizationMemberCreate(
            organization_id=invite['organization_id'],
            user_id=user_id,
            role=MemberRole.from_db_value(invite['role']) or MemberRole.VIEWER,
            invited_by=invite['invited_by'],
            invite_id=invite['id']
        )
        member = await add_organization_member(supabase, member_data)

        if member:
            # 3. Mark invite as accepted
            supabase.from_('invites').update({'status': 'accepted', 'accepted_at': datetime.now().isoformat()}).eq('id', str(invite['id'])).execute()
            return member
        return None
    except Exception as e:
        print(f"Error accepting invite: {e}")
        return None


async def create_registration_membership(
    organization_id: UUID,
    user_id: UUID,
    role: MemberRole,
) -> bool:
    """Persist a signup membership and verify that it was created.

    Registration must not report success until the user is linked to the
    organization; otherwise the approval queues cannot find the account.
    """
    try:
        with _connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO organization_members (organization_id, user_id, role)
                   VALUES (%s, %s, %s)
                   RETURNING id""",
                (str(organization_id), str(user_id), role.value),
            )
            created = cursor.fetchone() is not None
            connection.commit()
            return created
    except Exception as e:
        print(f"Error creating signup membership: {e}")
        return False
