import os
import httpx
import uuid
import asyncio
from pathlib import Path
from urllib.parse import urlparse

class AssetCollector:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.assets_media_dir = self.workspace_path / "assets" / "media"
        self.assets_media_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_urls = {} # url -> local_path

    async def _download_file(self, url: str) -> str:
        """Downloads a file if not already downloaded and returns the local relative path."""
        if not url or not url.startswith("http"):
            return url
            
        if url in self.downloaded_urls:
            return self.downloaded_urls[url]
            
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = f"asset_{uuid.uuid4().hex[:8]}.jpg"
            
        # Truncate filename to prevent Windows MAX_PATH errors (keep extension)
        name, ext = os.path.splitext(filename)
        if len(name) > 40:
            name = name[:40]
        filename = f"{name}{ext}"
            
        # Ensure unique filename
        local_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        local_path = self.assets_media_dir / local_filename
        
        try:
            async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
                response = await client.get(url, timeout=30.0)
                if response.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(response.content)
                    
                    # Return relative path for the offline HTML
                    relative_path = f"./assets/media/{local_filename}"
                    self.downloaded_urls[url] = relative_path
                    return relative_path
        except Exception as e:
            print(f"Failed to download asset {url}: {e}")
            
        return url

    async def download_all_assets(self, data: dict) -> dict:
        """
        Traverses the celebration data, downloads all media_url/video_url/profile_image fields,
        and rewrites them with local paths.
        """
        # Event profile image and media
        if "event" in data:
            for field in ["birthday_person_photo", "cover_url", "hero_video_url", "background_music_url"]:
                if field in data["event"] and data["event"][field]:
                    data["event"][field] = await self._download_file(data["event"][field])
            
        # Wishes media
        if "wishes" in data:
            for wish in data["wishes"]:
                if "media_url" in wish and wish["media_url"]:
                    wish["media_url"] = await self._download_file(wish["media_url"])
                    
        # Timeline media
        if "timeline" in data:
            for memory in data["timeline"]:
                if "media_url" in memory and memory["media_url"]:
                    memory["media_url"] = await self._download_file(memory["media_url"])
                    
        # Vault media
        if "vault" in data and data["vault"]:
            if "unlock_media_url" in data["vault"] and data["vault"]["unlock_media_url"]:
                data["vault"]["unlock_media_url"] = await self._download_file(data["vault"]["unlock_media_url"])
                
            # Vault wish media
            if "vault_wish" in data["vault"] and data["vault"]["vault_wish"]:
                if "media_url" in data["vault"]["vault_wish"] and data["vault"]["vault_wish"]["media_url"]:
                    data["vault"]["vault_wish"]["media_url"] = await self._download_file(data["vault"]["vault_wish"]["media_url"])

            # Secret wishes media
            if "secret_wishes" in data["vault"] and data["vault"]["secret_wishes"]:
                for wish in data["vault"]["secret_wishes"]:
                    if "media_url" in wish and wish["media_url"]:
                        wish["media_url"] = await self._download_file(wish["media_url"])
                
            # Vault dynamic_data media
            if "dynamic_data" in data["vault"]:
                dyn = data["vault"]["dynamic_data"]
                
                if "videoWish" in dyn and dyn["videoWish"]:
                    dyn["videoWish"] = await self._download_file(dyn["videoWish"])
                    
                if "photos" in dyn and isinstance(dyn["photos"], list):
                    for i, photo_url in enumerate(dyn["photos"]):
                        if photo_url:
                            dyn["photos"][i] = await self._download_file(photo_url)
                            
                if "timeline" in dyn and isinstance(dyn["timeline"], list):
                    for memory in dyn["timeline"]:
                        if "image" in memory and memory["image"]:
                            memory["image"] = await self._download_file(memory["image"])
                
        return data
