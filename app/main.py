import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.core.bootstrap import seed_system_data
from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, async_engine
from app.core.error_handlers import register_error_handlers
from app.core.middleware import (
    RequestCorrelationIdMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
)

# Configure structured root logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown lifecycle events."""
    logger.info(f"Starting {settings.PROJECT_NAME} (Environment: {settings.ENVIRONMENT})...")

    # 1. Initialize Tables in Development (if using SQLite fallback or initial dev DB)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Seed Initial System Data & Super Admin
    async with AsyncSessionLocal() as session:
        try:
            await seed_system_data(session)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error during system bootstrap: {str(e)}", exc_info=True)

    # 3. Ensure upload directories exist
    os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "candidates"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_DIR, "documents"), exist_ok=True)

    logger.info("Application startup completed successfully.")
    yield
    logger.info("Shutting down application...")


# FastAPI Application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-Grade Voting & Election Management System REST API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Register Custom Middleware (Order: Outer to Inner)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RequestCorrelationIdMiddleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms"]
)

# Register Centralized Error Handlers
register_error_handlers(app)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Mount Local Uploads directory if configured
if os.path.exists(settings.LOCAL_STORAGE_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.LOCAL_STORAGE_DIR), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
