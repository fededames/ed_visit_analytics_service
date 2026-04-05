from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.analytics import router as analytics_router
from app.db.session import get_db
from app.api.records import router as records_router

router = APIRouter()
router.include_router(records_router)
router.include_router(analytics_router)


@router.get("/health")
def healthcheck(session: Session = Depends(get_db)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
