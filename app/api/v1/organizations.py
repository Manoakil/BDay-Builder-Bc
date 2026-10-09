from typing import List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.database import get_supabase_client
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
from app.services import organization_service
from app.services import event_service
from app.dependencies import get_current_user

router = APIRouter()

class RejectRequest(BaseModel):
    rejection_reason: str | None = None


# =============================================
# ORGANIZATION ENDPOINTS
# =============================================

@router.get("/", response_model=List[Organization])
async def get_organizations(
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Get all organizations or organizations for current user.
    - Super Admin: sees all organizations
    - Regular users: sees only their organizations
    """
    # Check memberships as well as the profile role. Super admins are not
    # required to belong to every organization they manage.
    if organization_service.is_super_admin(current_user.id):
        return await organization_service.get_all_organizations(supabase)
    else:
        # Regular users see only their organizations
        return await organization_service.get_organizations_by_user(supabase, current_user.id)


@router.post("/", response_model=Organization, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_in: OrganizationCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Create a new organization.
    - Only Super Admin can create organizations
    """
    if not organization_service.is_super_admin(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only super_admin can create organizations"
        )
    
    org_in.created_by = current_user.id
    organization = await organization_service.create_organization_from_db(org_in)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Organization creation failed. Please check the data and try again."
        )
    
    return organization


@router.get("/pending-org-admins")
async def get_pending_org_admins(
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Super admin views org_admin signups awaiting approval.
    """
    if not organization_service.is_super_admin(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only super admin can view pending org admins"
        )
    return await organization_service.get_pending_org_admins()


@router.get("/global-members")
async def get_global_members(
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Super admin views all users and invites across the platform.
    """
    if not organization_service.is_super_admin(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only super admin can view all global members"
        )
    return await organization_service.get_all_global_members()

@router.get("/{org_id}", response_model=Organization)
async def get_organization(
    org_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Get organization by ID.
    - Users can only access organizations they are members of
    - Super Admin can access all organizations
    """
    organization = await organization_service.get_organization_by_id(supabase, org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if user has access
    if not organization_service.is_super_admin(current_user.id):
        is_member = organization_service.get_member_role(current_user.id, org_id) is not None
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization"
            )
    
    return organization


@router.put("/{org_id}", response_model=Organization)
async def update_organization(
    org_id: UUID,
    org_in: OrganizationUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Update organization.
    - Only Super Admin or Organization Admin can update
    """
    is_super_admin = organization_service.is_super_admin(current_user.id)
    is_org_admin = organization_service.is_org_admin(current_user.id, org_id)
    
    if not (is_super_admin or is_org_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or org admin can update organization"
        )
    
    organization = await organization_service.update_organization(supabase, org_id, org_in)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found or update failed")
    return organization


@router.post("/{org_id}/regenerate-code", response_model=Organization)
async def regenerate_secret_code(
    org_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Regenerate organization secret code.
    - Only Super Admin or Organization Admin can regenerate
    """
    is_super_admin = organization_service.is_super_admin(current_user.id)
    is_org_admin = organization_service.is_org_admin(current_user.id, org_id)
    
    if not (is_super_admin or is_org_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or org admin can regenerate secret code"
        )
    
    org = await organization_service.regenerate_secret_code(supabase, org_id)
    if not org:
        raise HTTPException(status_code=400, detail="Failed to regenerate secret code")
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> None:
    """
    Delete organization (soft delete).
    - Only Super Admin can delete organizations
    """
    if not organization_service.is_super_admin(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin can delete organization"
        )
    
    deleted = await organization_service.delete_organization(supabase, org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Organization not found")
    return None


# =============================================
# ORGANIZATION MEMBERS ENDPOINTS
# =============================================

@router.get("/{org_id}/events")
async def get_organization_events(
    org_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Coordinator event list used to resume an already initialized event."""
    if not organization_service.can_manage_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the organization admin can view event controls")
    return await event_service.get_events_by_organization_id(supabase, org_id)

@router.get("/{org_id}/members")
async def get_organization_members(
    org_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Get organization members with profile info.
    - Only members of the organization can view members
    """
    is_super_admin = organization_service.is_super_admin(current_user.id)
    is_org_admin = organization_service.is_org_admin(current_user.id, org_id)
    is_member = organization_service.get_member_role(current_user.id, org_id) is not None
    
    if not (is_super_admin or is_org_admin or is_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this organization"
        )
    
    return await organization_service.get_org_members_with_profiles(org_id)


@router.post("/{org_id}/members")
async def add_organization_member(
    org_id: UUID,
    member_in: OrganizationMemberCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Add a member to the organization.
    - Only Super Admin or Organization Admin can add members
    """
    is_super_admin = organization_service.is_super_admin(current_user.id)
    is_org_admin = organization_service.is_org_admin(current_user.id, org_id)
    
    if not (is_super_admin or is_org_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or org admin can add members"
        )

    if member_in.role.value == "super_admin" and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin can assign the super_admin role",
        )
    
    member_in.organization_id = org_id
    member = await organization_service.add_organization_member(supabase, member_in)
    if not member:
        raise HTTPException(status_code=400, detail="Failed to add member")
    return member


@router.put("/{org_id}/members/{member_id}")
async def update_organization_member(
    org_id: UUID,
    member_id: UUID,
    member_in: OrganizationMemberUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Update member's role or permissions.
    - Only Super Admin or Organization Admin can update members
    """
    is_super_admin = organization_service.is_super_admin(current_user.id)
    is_org_admin = organization_service.is_org_admin(current_user.id, org_id)
    
    if not (is_super_admin or is_org_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or org admin can update members"
        )

    if member_in.role and member_in.role.value == "super_admin" and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin can assign the super_admin role",
        )

    # The member ID must be scoped to the organization in the URL. Without
    # this, an Org Admin could submit another organization's member ID.
    if not organization_service.member_belongs_to_organization(member_id, org_id):
        raise HTTPException(status_code=404, detail="Member not found in this organization")
    
    member = await organization_service.update_organization_member(supabase, member_id, member_in)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found or update failed")
    return member


@router.delete("/{org_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    org_id: UUID,
    member_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> None:
    """
    Remove a member from the organization.
    - Only Super Admin or Organization Admin can remove members
    """
    is_super_admin = organization_service.is_super_admin(current_user.id)
    is_org_admin = organization_service.is_org_admin(current_user.id, org_id)
    
    if not (is_super_admin or is_org_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or org admin can remove members"
        )

    if not organization_service.member_belongs_to_organization(member_id, org_id):
        raise HTTPException(status_code=404, detail="Member not found in this organization")
    
    removed = await organization_service.remove_organization_member(supabase, member_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")
    return None


@router.post("/{org_id}/members/{user_id}/approve")
async def approve_member(
    org_id: UUID,
    user_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Approve a member's access to the organization.
    - org_admin signups are approved by Super Admin
    - Other members are approved by Organization Admin
    """
    target_role = organization_service.get_member_role(user_id, org_id)
    if not target_role:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    # org_admin signups are approved by super admin
    if target_role == 'org_admin':
        if not organization_service.is_super_admin(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Only super admin can approve org admins"
            )
    else:
        # Other members approved by org admin
        if not organization_service.is_org_admin(current_user.id, org_id) and not organization_service.is_super_admin(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Only org admin can approve members"
            )

    result = await organization_service.set_member_approval(
        user_id=user_id, 
        org_id=org_id, 
        approver_id=current_user.id, 
        decision='approved'
    )
    if not result:
        raise HTTPException(status_code=400, detail="Approval failed")
    return result


@router.post("/{org_id}/members/{user_id}/reject")
async def reject_member(
    org_id: UUID,
    user_id: UUID,
    body: Optional[RejectRequest] = None,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Reject a member's access request.
    - org_admin signups are rejected by Super Admin
    - Other members are rejected by Organization Admin
    """
    target_role = organization_service.get_member_role(user_id, org_id)
    if not target_role:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    # org_admin signups are rejected by super admin
    if target_role == 'org_admin':
        if not organization_service.is_super_admin(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Only super admin can reject org admins"
            )
    else:
        # Other members rejected by org admin
        if not organization_service.is_org_admin(current_user.id, org_id) and not organization_service.is_super_admin(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Only org admin can reject members"
            )

    reason = body.rejection_reason if body else None
    result = await organization_service.set_member_approval(
        user_id=user_id, 
        org_id=org_id, 
        approver_id=current_user.id, 
        decision='rejected', 
        rejection_reason=reason
    )
    if not result:
        raise HTTPException(status_code=400, detail="Rejection failed")
    return result


# =============================================
# INVITES ENDPOINTS
# =============================================

@router.post("/{org_id}/invites", response_model=Invite, status_code=status.HTTP_201_CREATED)
async def create_invite(
    org_id: UUID,
    invite_in: InviteCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Create an invite for a new member.
    - Only Super Admin or Organization Admin can create invites
    """
    is_super_admin = organization_service.is_super_admin(current_user.id)
    is_org_admin = organization_service.is_org_admin(current_user.id, org_id)
    
    if not (is_super_admin or is_org_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or org admin can create invites"
        )
    
    invite_in.organization_id = org_id
    invite_in.invited_by = current_user.id
    invite = await organization_service.create_invite(supabase, invite_in)
    if not invite:
        raise HTTPException(status_code=400, detail="Invite creation failed")
    return invite


@router.post("/invites/{token}/accept", response_model=OrganizationMember, status_code=status.HTTP_201_CREATED)
async def accept_invite(
    token: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    """
    Accept an invite using the token.
    - Anyone with a valid token can accept
    """
    member = await organization_service.accept_invite(supabase, token, current_user.id)
    if not member:
        raise HTTPException(status_code=400, detail="Invite invalid or already used")
    return member
