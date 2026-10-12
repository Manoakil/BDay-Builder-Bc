from supabase import Client
from app.schemas.event import Event
from app.services import wish_service, timeline_service
from typing import List, Dict

class PackageBuilder:
    def __init__(self, supabase: Client, event: Event):
        self.supabase = supabase
        self.event = event
        
    async def generate_data_payload(self, start_step: str = "welcome") -> dict:
        """
        Extracts all relevant celebration data into a serializable dict.
        """
        # Event Details
        event_schema = self.event.model_dump(mode="json")
        
        # Approved Wishes (including public wishes)
        public_wishes = await wish_service.get_approved_wishes_by_event_id(self.supabase, self.event.id)
        wishes_data = [w.model_dump(mode="json") for w in public_wishes] if public_wishes else []
        
        # Memory Timeline
        timeline = await timeline_service.get_timeline_entries_by_event_id(self.supabase, self.event.id)
        timeline_data = [t.model_dump(mode="json") for t in timeline] if timeline else []

        # Secret Vault
        vault_data = None
        vault_response = self.supabase.table("secret_vault").select("*").eq("event_id", str(self.event.id)).order("created_at", desc=True).execute()
        if vault_response.data and len(vault_response.data) > 0:
            vault = vault_response.data[0]
            dyn_data = vault.get("dynamic_data") or {}
            
            vault_wish_data = None
            vault_wish_id = vault.get("vault_wish_id")
            if vault_wish_id:
                try:
                    vault_wish = await wish_service.get_wish_by_id(self.supabase, vault_wish_id)
                    if vault_wish:
                        vault_wish_data = vault_wish.model_dump(mode="json")
                except Exception as e:
                    print(f"Error fetching vault wish in package builder: {e}")
            
            # Fetch secret wishes if any
            secret_wishes = []
            try:
                secret_wishes = await wish_service.get_secret_wishes_by_event_id(self.supabase, self.event.id)
            except Exception as e:
                print(f"Error fetching secret wishes in package builder: {e}")

            vault_data = {
                "id": str(vault.get("id")),
                "event_id": str(self.event.id),
                "is_enabled": vault.get("is_enabled", True),
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
            "vault": vault_data,
            "start_step": start_step
        }
