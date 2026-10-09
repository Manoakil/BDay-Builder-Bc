from fastapi import APIRouter
from . import wishes
from . import analytics
from . import auth

from . import events
from . import gallery
from . import organizations
from . import themes
from . import timeline
from . import upload
from . import vault
from . import audit
from . import offline_celebration

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(wishes.router, prefix="/wishes", tags=["Wishes"])
api_router.include_router(gallery.router, prefix="/gallery", tags=["Gallery"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["Timeline"])
api_router.include_router(vault.router, prefix="/vault", tags=["Secret Vault"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(themes.router, prefix="/themes", tags=["Themes"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["audit"])
api_router.include_router(offline_celebration.router, prefix="/offline-celebration", tags=["Offline Celebration"])
