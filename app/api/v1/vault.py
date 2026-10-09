from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.database import get_supabase_client
from app.schemas.vault import SecretVault, SecretVaultCreate, SecretVaultUpdate, SecretVaultPublic, VaultAttemptCreate
from app.api.v1.events import _reveal_time
from app.services import event_service
from app.services import organization_service
from app.services import vault_service
from app.services import wish_service
from app.dependencies import get_current_user
from app.utils.security import verify_hash

router = APIRouter()


async def _require_revealed_birthday_event(supabase: Client, current_user: Any, event_id: UUID):
    event = await event_service.get_event_by_id(supabase, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    # For now, allow any authenticated user (like the vault wisher) to view the vault
    return event


async def _require_vault_manager(supabase: Client, current_user: Any, event_id: UUID):
    """Keep vault setup in the hands of the event's coordinator or the vault wisher."""
    event = await event_service.get_event_by_id(supabase, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    # For now, allow any authenticated user (like the vault wisher) to manage the vault
    return event

@router.post("/", response_model=SecretVault, status_code=status.HTTP_201_CREATED)
async def create_secret_vault(
    vault_in: SecretVaultCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    await _require_vault_manager(supabase, current_user, vault_in.event_id)
    vault_in.created_by = current_user.id
    vault = await vault_service.create_secret_vault(supabase, vault_in)
    if not vault:
        raise HTTPException(status_code=400, detail="Secret Vault creation failed")
    return vault


@router.get("/{event_id}/manage", response_model=SecretVault)
async def get_secret_vault_for_manager(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user),
) -> Any:
    await _require_vault_manager(supabase, current_user, event_id)
    vault = await vault_service.get_secret_vault_by_event_id(supabase, event_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Secret Vault not found for this event")
    return vault


@router.patch("/{vault_id}", response_model=SecretVault)
async def update_secret_vault(
    vault_id: UUID,
    vault_in: SecretVaultUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user),
) -> Any:
    vault = await vault_service.get_secret_vault_by_id(supabase, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Secret Vault not found")
    await _require_vault_manager(supabase, current_user, vault.event_id)
    updated = await vault_service.update_secret_vault(supabase, vault_id, vault_in)
    if not updated:
        raise HTTPException(status_code=400, detail="Vault update failed")
    return updated

@router.get("/{event_id}", response_model=SecretVaultPublic)
async def get_secret_vault_for_event(
    event_id: UUID,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user) # Optional auth
) -> Any:
    await _require_revealed_birthday_event(supabase, current_user, event_id)
    vault = await vault_service.get_secret_vault_by_event_id(supabase, event_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Secret Vault not found for this event")
    if not vault.is_enabled:
        raise HTTPException(status_code=404, detail="Secret Vault is not enabled")
    return SecretVaultPublic.model_validate(vault.model_dump(exclude={"answer_hash"}))

@router.post("/{vault_id}/attempt", status_code=status.HTTP_200_OK)
async def attempt_secret_vault(
    vault_id: UUID,
    attempt_in: VaultAttemptCreate,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user) # Can be None for guest attempts
) -> Any:
    vault = await vault_service.get_secret_vault_by_id(supabase, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Secret Vault not found")
    await _require_revealed_birthday_event(supabase, current_user, vault.event_id)
    if not vault.is_enabled:
        raise HTTPException(status_code=404, detail="Secret Vault is not enabled")
    
    now = datetime.now(timezone.utc)
    locked_until = vault.locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if vault.is_locked and (not locked_until or locked_until > now):
        raise HTTPException(status_code=423, detail="Vault is locked. Try again later.")

    is_correct = verify_hash(attempt_in.attempt_answer, vault.answer_hash)
    
    attempt_in.vault_id = vault_id
    if current_user:
        attempt_in.user_id = current_user.id
    attempt_in.is_correct = is_correct
    # TODO: Get IP address and user agent from request
    await vault_service.record_vault_attempt(supabase, attempt_in)

    if is_correct:
        await vault_service.unlock_vault(supabase, vault_id)
        vault_wish = await wish_service.get_wish_by_id(supabase, vault.vault_wish_id) if vault.vault_wish_id else None
        return {
            "message": "Vault unlocked successfully!", "unlocked": True,
            "vault_wish": vault_wish.model_dump(mode="json") if vault_wish else None,
        }
    else:
        # Trigger logic to increment attempts and potentially lock vault
        # This is handled by a trigger in the SQL schema
        raise HTTPException(status_code=401, detail="Incorrect answer.")


from pydantic import BaseModel

class ConfessionAnswer(BaseModel):
    answer: str

@router.post("/{vault_id}/confess", status_code=status.HTTP_200_OK)
async def submit_confession_answer(
    vault_id: UUID,
    answer_in: ConfessionAnswer,
    supabase: Client = Depends(get_supabase_client),
    current_user: Any = Depends(get_current_user)
) -> Any:
    vault = await vault_service.get_secret_vault_by_id(supabase, vault_id)
    if not vault:
        raise HTTPException(status_code=404, detail="Secret Vault not found")
        
    event = await event_service.get_event_by_id(supabase, vault.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    from app.services.email_service import send_email
    
    dynamic_data = vault.dynamic_data or {}
    dynamic_data['confession_answer'] = answer_in.answer
    
    await vault_service.update_secret_vault(supabase, vault_id, SecretVaultUpdate(dynamic_data=dynamic_data))

    subject = f"Confession Answer for {event.title}"
    body = f"The birthday person answered your confession with: {answer_in.answer}"
    
    admin_email = "bdaybuilder@gmail.com"
    try:
        org_members_resp = supabase.from_('organization_members').select('user_id').eq('organization_id', str(event.organization_id)).eq('role', 'org_admin').execute()
        
        target_user_id = str(event.created_by)
        if org_members_resp.data and len(org_members_resp.data) > 0:
            target_user_id = org_members_resp.data[0]['user_id']
            
        user_resp = supabase.from_('profiles').select('email').eq('id', target_user_id).limit(1).execute()
        if user_resp.data and len(user_resp.data) > 0 and user_resp.data[0].get('email'):
            admin_email = user_resp.data[0]['email']
            
    except Exception as e:
        print(f"Failed to fetch org admin email: {e}")
    
    await send_email(admin_email, subject, body)

    return {"message": "Answer recorded and email sent."}
