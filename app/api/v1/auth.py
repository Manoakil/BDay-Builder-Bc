from datetime import timedelta, date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from supabase import Client

from app.config import settings
from app.database import get_supabase_client
from app.schemas.auth import Token
from app.schemas.user import UserCreate, User
from app.schemas.common import MemberRole, UserStatus
from app.services import auth_service, organization_service

router = APIRouter()


class SecretCodeRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    secret_code: str
    role: MemberRole  # wisher, bday_person or org_admin
    date_of_birth: date | None = None

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        """Accept legacy UI role labels while storing canonical role values."""
        aliases = {
            "admin": "org_admin",
            "org-admin": "org_admin",
            "birthday_person": "bday_person",
            "birthday-person": "bday_person",
        }
        return aliases.get(value, value)


@router.post("/register-with-code", response_model=User)
async def register_with_secret_code(
    data: SecretCodeRegister,
    supabase: Client = Depends(get_supabase_client)
) -> Any:
    """Wishers, birthday persons and org admins register using the org secret code."""
    # Normalize input here too, so direct API clients and pasted invite codes
    # behave exactly like the frontend.
    data.secret_code = data.secret_code.strip().upper()

    # 1. Validate secret code and find org
    org_resp = supabase.from_('organizations').select('id, secret_code').eq('secret_code', data.secret_code).execute()
    if not org_resp.data:
        raise HTTPException(status_code=400, detail="Invalid secret code")
    org_id = org_resp.data[0]['id']

    # 2. Allowed roles via this route: wisher, bday_person, org_admin
    if data.role not in (MemberRole.wisher, MemberRole.bday_person, MemberRole.org_admin):
        raise HTTPException(status_code=400, detail="Invalid role for this registration method")
        
    # Check if organization has an approved org_admin or super_admin
    if data.role in (MemberRole.wisher, MemberRole.bday_person):
        admins_resp = supabase.from_('organization_members') \
            .select('user_id') \
            .eq('organization_id', org_id) \
            .in_('role', ['org_admin', 'super_admin']) \
            .is_('deleted_at', 'null') \
            .execute()
            
        if not admins_resp.data:
            raise HTTPException(
                status_code=400, 
                detail="This organization is not yet active. Please wait for an Organization Admin to set it up."
            )
            
        admin_ids = [m['user_id'] for m in admins_resp.data]
        profiles_resp = supabase.from_('profiles') \
            .select('id') \
            .in_('id', admin_ids) \
            .eq('approval_status', 'approved') \
            .execute()
            
        if not profiles_resp.data:
            raise HTTPException(
                status_code=400,
                detail="This organization is not yet active. Please wait for an Organization Admin to be approved."
            )

    duplicate_field = organization_service.registration_identity_exists(data.email)
    if duplicate_field:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with this {duplicate_field} already exists. Please sign in instead.",
        )

    # 3. Determine approval status
    #    - org_admin signs up pending, must be approved by super admin
    #    - wisher / bday_person sign up pending, must be approved by org admin
    #    - EXCEPTION: bday_person signing up ON their birthday is auto-approved
    effective_role = data.role.value  # wisher | bday_person | org_admin
    initial_approval = "pending"
    initial_status = UserStatus.pending_approval

    if data.role == MemberRole.bday_person and data.date_of_birth:
        today = date.today()
        dob = data.date_of_birth
        if dob.month == today.month and dob.day == today.day:
            initial_approval = "approved"
            initial_status = UserStatus.active

    # 4. Register user with calculated status/approval
    user_in = UserCreate(email=data.email, password=data.password, full_name=data.full_name)
    user = await auth_service.register_user(
        supabase,
        user_in,
        initial_status=initial_status,
        initial_approval=initial_approval,
        signup_secret_code=data.secret_code,
    )
    if not user:
        raise HTTPException(status_code=400, detail="Registration failed")

    # 5. Store date_of_birth on profile
    if data.date_of_birth:
        supabase.from_('profiles').update({
            "date_of_birth": data.date_of_birth.isoformat(),
            "approval_status": initial_approval,
            "status": initial_status.value,
        }).eq('id', str(user.id)).execute()

    # 6. Add the user to this organization and verify it was persisted. The
    # approval queues operate on organization_members, so returning success
    # without this record would create an unapprovable account.
    membership_created = await organization_service.create_registration_membership(
        UUID(org_id), user.id, data.role
    )
    if not membership_created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account was created but could not be linked to the organization. Please contact support.",
        )

    return user


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    supabase: Client = Depends(get_supabase_client)
) -> Any:
    user = await auth_service.authenticate_user(supabase, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.approval_status == 'pending':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval by an administrator."
        )
    elif user.approval_status == 'rejected':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account request was rejected. Reason: {user.rejection_reason or 'No reason provided.'}"
        )

    # Use effective role resolved during authentication
    role_slug = user.role_slug or "viewer"

    # Permanent token for super_admin/org_admin, timed token for everyone else
    is_permanent = role_slug in ("super_admin", "super_admin", "org_admin")
    expires_delta = (
        None if is_permanent
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "role": role_slug or "viewer"}, expires_delta=expires_delta
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(
    supabase: Client = Depends(get_supabase_client),
    token: str = Depends(__import__('fastapi.security', fromlist=['OAuth2PasswordBearer']).OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login"))
) -> Any:
    payload = __import__('jose', fromlist=['jwt']).jwt.decode(
        token, __import__('app.config', fromlist=['settings']).settings.JWT_SECRET_KEY,
        algorithms=[__import__('app.config', fromlist=['settings']).settings.ALGORITHM],
        options={"verify_exp": False}
    )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    try:
        resp = supabase.from_('profiles').select('*').eq('id', user_id).execute()
        if resp.data and len(resp.data) > 0:
            profile = resp.data[0]
            return {
                "user_id": user_id, 
                "role": payload.get("role"),
                "full_name": profile.get("full_name"),
                "email": profile.get("email")
            }
    except Exception as e:
        print(f"Failed to fetch profile in /me: {e}")
        
    return {"user_id": user_id, "role": payload.get("role")}
