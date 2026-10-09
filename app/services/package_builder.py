from supabase import Client
from app.schemas.event import Event
from app.services import wish_service, timeline_service
from typing import List, Dict

class PackageBuilder:
    def __init__(self, supabase: Client, event: Event):
        self.supabase = supabase
        self.event = event
        
    async def generate_data_payload(self) -> dict:
        """
        Extracts all relevant celebration data into a serializable dict.
        """
        # Event Details
        event_schema = self.event.model_dump(mode="json")
        
        # Secret Vault
        vault_data = None
        vault_creator_id = None
        vault_response = self.supabase.table("secret_vault").select("*").eq("event_id", str(self.event.id)).order("created_at", desc=True).execute()
        if vault_response.data and len(vault_response.data) > 0:
            vault = vault_response.data[0]
            vault_creator_id = vault.get("created_by")

        # Approved Wishes (including secret ones)
        public_wishes = await wish_service.get_approved_wishes_by_event_id(self.supabase, self.event.id)
        secret_wishes = await wish_service.get_secret_wishes_by_event_id(self.supabase, self.event.id)
        wishes = public_wishes
        wishes_data = [w.model_dump(mode="json") for w in wishes]
        
        # Memory Timeline
        timeline = await timeline_service.get_timeline_entries_by_event_id(self.supabase, self.event.id)
        timeline_data = [t.model_dump(mode="json") for t in timeline]
        
        # Process Vault Data
        if vault_creator_id:
            dyn_data = vault.get("dynamic_data") or {}
            
            vault_wish_data = None
            vault_wish_id = vault.get("vault_wish_id")
            if vault_wish_id:
                vault_wish = await wish_service.get_wish_by_id(self.supabase, vault_wish_id)
                if vault_wish:
                    vault_wish_data = vault_wish.model_dump(mode="json")
            
            # Check confession answer
            if dyn_data.get("confession_answer") == "no":
                vault_data = None
            elif vault.get("is_enabled"):
                vault_data = {
                    "question": vault.get("question"),
                    "hint": vault.get("hint"),
                    "unlock_message": vault.get("unlock_message"),
                    "unlock_media_url": vault.get("unlock_media_url"),
                    "is_locked": False, # Always unlocked in offline mode
                    "dynamic_data": dyn_data,
                    "vault_wish": vault_wish_data,
                    "secret_wishes": [w.model_dump(mode="json") for w in secret_wishes] if secret_wishes else []
                }
            
        return {
            "event": event_schema,
            "wishes": wishes_data,
            "timeline": timeline_data,
            "vault": vault_data
        }
