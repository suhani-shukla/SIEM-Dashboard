from fastapi import APIRouter

from app.api.v1.events import router as events_router
from app.api.v1.playbooks import router as playbooks_router
from app.api.v1 import alerts

router = APIRouter()

router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
router.include_router(events_router)
router.include_router(playbooks_router)