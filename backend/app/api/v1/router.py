from fastapi import APIRouter

from app.api.v1.events import router as events_router

router = APIRouter(prefix="/api/v1")
router.include_router(events_router)
