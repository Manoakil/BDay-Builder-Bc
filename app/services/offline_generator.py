import os
import shutil
import tempfile
import uuid
import json
from pathlib import Path
from supabase import Client
from app.schemas.event import Event
from .asset_collector import AssetCollector
from .package_builder import PackageBuilder
from .zip_service import create_zip_package

async def build_offline_package(supabase: Client, event: Event, start_step: str = "welcome") -> str:
    """
    Coordinates the offline package generation.
    Returns the path to the generated ZIP file.
    """
    # Create a temporary workspace
    workspace = Path(tempfile.mkdtemp(prefix=f"birthday-export-{event.id}-"))
    
    try:
        # Define paths
        assets_dir = workspace / "assets"
        data_dir = workspace / "data"
        assets_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Fetch all data and build the CELEBRATION_DATA structure
        package_builder = PackageBuilder(supabase, event)
        celebration_data = await package_builder.generate_data_payload(start_step=start_step)
        
        # 2. Collect all assets and update the payload with local paths
        asset_collector = AssetCollector(workspace)
        celebration_data = await asset_collector.download_all_assets(celebration_data)
        
        # 3. Write data/celebration.js
        data_file = data_dir / "celebration.js"
        with open(data_file, "w", encoding="utf-8") as f:
            f.write(f"window.CELEBRATION_DATA = {json.dumps(celebration_data, indent=2)};\n")
            
        # 4. Copy frontend build files
        possible_paths = [
            Path(__file__).resolve().parent.parent / "offline_template",
            Path(__file__).resolve().parents[2] / "offline_template",
            Path("v:/Varsha/frontend/build"),
            Path(__file__).resolve().parents[3] / "frontend" / "build",
            Path.cwd() / "frontend" / "build",
            Path.cwd().parent / "frontend" / "build",
            Path.cwd() / "offline_template",
        ]
        frontend_build_path = None
        for p in possible_paths:
            if p.exists() and (p / "index.html").exists():
                frontend_build_path = p
                break

        if not frontend_build_path:
            raise FileNotFoundError(
                "Frontend build folder not found. Please ensure 'npm run build' has been run in the frontend directory."
            )
            
        for item in frontend_build_path.iterdir():
            if item.is_dir():
                shutil.copytree(item, workspace / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, workspace)
                
        # Inject the data script into index.html and ensure relative paths
        index_file = workspace / "index.html"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Convert root-relative URLs to relative URLs so offline file:// and local servers can find static JS/CSS
            content = content.replace('src="/static/', 'src="./static/')
            content = content.replace('href="/static/', 'href="./static/')
            content = content.replace('href="/manifest.json"', 'href="./manifest.json"')
            content = content.replace('href="/icons8', 'href="./icons8')
            content = content.replace('href="/favicon', 'href="./favicon')

            # Inject celebration data BEFORE deferred React scripts in <head>
            script_tag = '<script src="./data/celebration.js"></script>'
            if "<head>" in content:
                content = content.replace("<head>", f"<head>\n    {script_tag}")
            elif "</head>" in content:
                content = content.replace("</head>", f"    {script_tag}\n</head>")
            else:
                content = f"{script_tag}\n{content}"
                
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(content)

        # 5. Zip it
        zip_path = workspace.with_suffix('.zip')
        create_zip_package(workspace, zip_path)
        
        return str(zip_path)
        
    finally:
        # We leave the ZIP file for the response to read, 
        # but we can optionally clean up the unzipped workspace here.
        # Wait, the FileResponse handles cleanup if we use background tasks,
        # but for now we just clean the workspace folder.
        shutil.rmtree(workspace, ignore_errors=True)
