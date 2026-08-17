from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/live")
async def liveness_probe() -> Dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    db_ok = False
    redis_ok = False
    details = {}

    # Check Database
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        details["database"] = "connected"
    except Exception as e:
        details["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        await r.ping()
        redis_ok = True
        details["redis"] = "connected"
        await r.aclose()
    except Exception as e:
        details["redis"] = f"offline/error: {str(e)}"

    overall_ready = db_ok # DB is required; Redis can fallback to memory in local dev

    status_code = status.HTTP_200_OK if overall_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": overall_ready,
            "checks": details
        }
    )
