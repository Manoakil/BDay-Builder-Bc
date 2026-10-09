from datetime import datetime, timedelta, date
from typing import Optional
from uuid import UUID

from jose import jwt, JWTError
from passlib.context import CryptContext
from supabase import Client
from app.config import settings
from app.schemas.user import UserCreate, User
from app.schemas.common import UserStatus

from app.utils.security import get_password_hash, verify_password

def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta is not None:
        to_encode.update({"exp": datetime.utcnow() + expires_delta})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


async def register_user(
    supabase: Client,
    user_in: UserCreate,
    initial_status: UserStatus = UserStatus.active,
    initial_approval: str = "approved",
    signup_secret_code: Optional[str] = None,
    date_of_birth: Optional[date] = None,
) -> Optional[User]:
    """Sign up a user with Supabase Auth and create a profile entry."""
    try:
        user_response = supabase.auth.sign_up({
            "email": user_in.email,
            "password": user_in.password
        })
        user_id = user_response.user.id
    except Exception as e:
        print(f"Supabase sign up error: {e}")
        return None

    # Default role is 'guest'/'viewer' in the roles table; slug is 'viewer'
    try:
        default_role_response = supabase.from_('roles').select('id').eq('slug', 'viewer').single().execute()
        default_role_id = default_role_response.data['id']
    except Exception as e:
        print(f"Error fetching default role: {e}")
        default_role_id = None

    try:
        profile_data = {
            "id": user_id,
            "full_name": user_in.full_name,
            "email_verified": user_response.user.email_confirmed_at is not None,
            "status": initial_status.value,
            "role_id": default_role_id,
            "approval_status": initial_approval,
            "signup_secret_code": signup_secret_code,
            "date_of_birth": date_of_birth.isoformat() if date_of_birth else None,
        }
        profile_response = supabase.from_('profiles').insert(profile_data).execute()
        if profile_response.data:
            return User(
                id=user_id,
                email=user_in.email,
                full_name=user_in.full_name,
                created_at=user_response.user.created_at,
                status=initial_status,
                role_id=default_role_id,
            )
        return None
    except Exception as e:
        print(f"Profile creation error: {e}")
        return None


async def authenticate_user(supabase: Client, email: str, password: str) -> Optional[User]:
    try:
        user_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if not user_response.user:
            return None

        auth_user = user_response.user
        user_id = auth_user.id

        # Fetch profile + approval status using Supabase HTTP client instead of psycopg2
        profile_response = supabase.from_('profiles').select(
            'full_name, avatar_url, status, role_id, approval_status, rejection_reason'
        ).eq('id', str(user_id)).execute()
        
        if not profile_response.data:
            print(f"No profile found for user {user_id}")
            return None
            
        row = profile_response.data[0]
        full_name = row.get('full_name')
        avatar_url = row.get('avatar_url')
        status = row.get('status')
        role_id = row.get('role_id')
        approval_status = row.get('approval_status')
        rejection_reason = row.get('rejection_reason')

        # Resolve effective role from organization_members (highest privilege)
        org_response = supabase.from_('organization_members').select('role').eq('user_id', str(user_id)).is_('deleted_at', 'null').execute()
        
        role_slug = None
        if org_response.data:
            # Sort manually according to privilege hierarchy
            privilege_order = {'super_admin': 1, 'org_admin': 2, 'bday_person': 3, 'wisher': 4}
            sorted_roles = sorted(org_response.data, key=lambda x: privilege_order.get(x.get('role'), 5))
            role_slug = sorted_roles[0].get('role')

        # Fall back to roles table slug if no org membership
        if not role_slug and role_id:
            role_response = supabase.from_('roles').select('slug').eq('id', str(role_id)).execute()
            if role_response.data:
                role_slug = role_response.data[0].get('slug')
            else:
                role_slug = "viewer"
        elif not role_slug:
            role_slug = "viewer"

        created_at = auth_user.created_at
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        return User(
            id=user_id,
            email=auth_user.email,
            full_name=full_name,
            avatar_url=avatar_url,
            status=status if status else 'active',
            role_id=role_id,
            role_slug=role_slug,
            created_at=created_at,
            approval_status=approval_status,
            rejection_reason=rejection_reason,
        )
    except Exception as e:
        print(f"Supabase authentication error: {e}")
        return None


async def get_user_by_id(supabase: Client, user_id: UUID) -> Optional[User]:
    try:
        import psycopg2
        db_url = settings.DATABASE_URL.strip('"')
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "SELECT p.full_name, p.avatar_url, p.status, p.role_id, p.approval_status "
            "FROM profiles p WHERE p.id = %s",
            (str(user_id),)
        )
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return None

        auth_user_response = supabase.auth.admin.get_user_by_id(str(user_id))
        auth_user_data = auth_user_response.user
        created_at = auth_user_data.created_at
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        return User(
            id=user_id,
            email=auth_user_data.email,
            full_name=row[0],
            avatar_url=row[1],
            status=row[2],
            role_id=row[3],
            created_at=created_at,
            approval_status=row[4],
        )
    except Exception as e:
        print(f"Error fetching user by ID: {e}")
        return None
