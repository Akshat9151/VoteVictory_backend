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
from app.core.tracing import configure_tracing

# Configure structured root logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("app.main")


import asyncio
from sqlalchemy import text

async def keep_neon_alive():
    """Background heartbeat to keep serverless Neon DB warm and prevent cold-start latency."""
    while True:
        try:
            await asyncio.sleep(120)  # Ping every 2 minutes
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
        except asyncio.CancelledError:
            break
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown lifecycle events."""
    logger.info(f"Starting {settings.PROJECT_NAME} (Environment: {settings.ENVIRONMENT})...")

    # 1. Initialize PostgreSQL Database Tables & Relations
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

    # 4. Start background database keep-alive task
    keep_alive_task = asyncio.create_task(keep_neon_alive())

    logger.info("Application startup completed successfully with PostgreSQL database.")
    yield
    keep_alive_task.cancel()
    logger.info("Shutting down application...")



# FastAPI Application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-Grade Voting & Election Management System REST API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Register Custom Error Handlers
register_error_handlers(app)

# Initialize tracing if dependencies are available
configure_tracing(app)

# Custom Enterprise Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RequestCorrelationIdMiddleware)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|.*\.vercel\.app)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Uploads (for candidate photos, documents, and exported reports)
uploads_dir = os.path.abspath(settings.LOCAL_STORAGE_DIR)
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Include Core API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root_status():
    """Root status endpoint returning service metadata."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "PostgreSQL",
        "docs": "/docs",
    }


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Lightweight health / warm-up endpoint. Called by the frontend on page load
    so the Render free-tier server is already awake by the time the user hits Sign In."""
    return {"status": "ok", "service": settings.PROJECT_NAME}
