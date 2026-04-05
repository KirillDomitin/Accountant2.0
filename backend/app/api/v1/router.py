from fastapi import APIRouter

from app.api.v1.endpoints.history import router as history_router
from app.api.v1.endpoints.inn import router as inn_router
from app.api.v1.endpoints.tracking import router as tracking_router

router = APIRouter()
router.include_router(inn_router)
router.include_router(history_router)
router.include_router(tracking_router)
