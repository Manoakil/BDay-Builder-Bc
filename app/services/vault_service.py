from typing import Optional, List
from uuid import UUID
from datetime import datetime

from supabase import Client

from app.schemas.vault import SecretVault, SecretVaultCreate, SecretVaultUpdate, VaultAttempt, VaultAttemptCreate, VaultMedia, VaultMediaCreate, VaultMediaUpdate
from app.utils.security import get_password_hash # Assuming get_password_hash is used for vault answers

async def create_secret_vault(supabase: Client, vault_in: SecretVaultCreate) -> Optional[SecretVault]:
    try:
        # Hash the answer before storing it
        vault_in.answer_hash = get_password_hash(vault_in.answer_hash)
        response = supabase.from_('secret_vault').insert(vault_in.model_dump(mode='json')).execute()
        if response.data:
            return SecretVault.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error creating secret vault: {e}")
        return None

async def get_secret_vault_by_event_id(supabase: Client, event_id: UUID) -> Optional[SecretVault]:
    try:
        response = supabase.from_('secret_vault').select('*').eq('event_id', str(event_id)).order('created_at', desc=True).limit(1).execute()
        if response.data and len(response.data) > 0:
            return SecretVault.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error fetching secret vault by event ID: {e}")
        return None

async def get_secret_vault_by_id(supabase: Client, vault_id: UUID) -> Optional[SecretVault]:
    try:
        response = supabase.from_('secret_vault').select('*').eq('id', str(vault_id)).maybe_single().execute()
        if response.data:
            return SecretVault.model_validate(response.data)
        return None
    except Exception as e:
        print(f"Error fetching secret vault by ID: {e}")
        return None

async def update_secret_vault(supabase: Client, vault_id: UUID, vault_in: SecretVaultUpdate) -> Optional[SecretVault]:
    try:
        # If answer_hash is updated, re-hash it
        if vault_in.answer_hash:
            vault_in.answer_hash = get_password_hash(vault_in.answer_hash)
        response = supabase.from_('secret_vault').update(vault_in.model_dump(mode='json', exclude_unset=True)).eq('id', str(vault_id)).execute()
        if response.data:
            return SecretVault.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error updating secret vault: {e}")
        return None

async def record_vault_attempt(supabase: Client, attempt_in: VaultAttemptCreate) -> Optional[VaultAttempt]:
    try:
        response = supabase.from_('vault_attempts').insert(attempt_in.model_dump(mode='json')).execute()
        if response.data:
            return VaultAttempt.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error recording vault attempt: {e}")
        return None

async def unlock_vault(supabase: Client, vault_id: UUID) -> Optional[SecretVault]:
    try:
        # Fetch current unlock_count first, then increment in a separate update
        current = supabase.from_('secret_vault').select('unlock_count').eq('id', str(vault_id)).single().execute()
        if not current.data:
            return None
        new_count = current.data['unlock_count'] + 1
        response = supabase.from_('secret_vault').update({
            'is_locked': False,
            'unlock_count': new_count,
            'unlock_time': datetime.now().isoformat()
        }).eq('id', str(vault_id)).execute()
        if response.data:
            return SecretVault.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error unlocking vault: {e}")
        return None

async def add_vault_media(supabase: Client, media_in: VaultMediaCreate) -> Optional[VaultMedia]:
    try:
        response = supabase.from_('vault_media').insert(media_in.model_dump(mode='json')).execute()
        if response.data:
            return VaultMedia.model_validate(response.data[0])
        return None
    except Exception as e:
        print(f"Error adding vault media: {e}")
        return None

async def get_vault_media_by_vault_id(supabase: Client, vault_id: UUID) -> List[VaultMedia]:
    try:
        response = supabase.from_('vault_media').select('*').eq('vault_id', str(vault_id)).order('sort_order').execute()
        if response.data:
            return [VaultMedia.model_validate(item) for item in response.data]
        return []
    except Exception as e:
        print(f"Error fetching vault media: {e}")
        return []

async def delete_vault_media(supabase: Client, media_id: UUID) -> bool:
    try:
        response = supabase.from_('vault_media').delete().eq('id', str(media_id)).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error deleting vault media: {e}")
        return False
