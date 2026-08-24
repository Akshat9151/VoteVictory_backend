from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General
    PROJECT_NAME: str = "ElectWin - Election Campaign Management System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ENABLE_TRACING: bool = True
    OTEL_SERVICE_NAME: str = "electwin-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "super-secret-system-key-change-in-production-0123456789abcdef"

    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        "https://voting-managment-front-end.vercel.app"
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./electwin_dev.db"
    DATABASE_SYNC_URL: str = "sqlite:///./electwin_dev.db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # Election Commission Statutory Budget Limit (₹1,50,000 ceiling)
    STATUTORY_BUDGET_LIMIT: float = 150000.0

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_TTL_SECONDS: int = 604800  # 7 days
    RATE_LIMIT_PER_MINUTE: int = 120
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 15
    RATE_LIMIT_BROADCAST_PER_MINUTE: int = 10
    AUDIENCE_SPLIT_CACHE_TTL_SECONDS: int = 300

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Security & Tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    PASSWORD_HASH_SCHEME: str = "argon2" # argon2 | bcrypt
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # Super Admin Bootstrap
    FIRST_SUPER_ADMIN_PHONE: str = "+91 98290 14285"
    FIRST_SUPER_ADMIN_EMAIL: str = "superadmin@electwin.com"
    FIRST_SUPER_ADMIN_PASSWORD: str = "SuperSecureAdminPassword123!"
    FIRST_SUPER_ADMIN_FIRST_NAME: str = "Super"
    FIRST_SUPER_ADMIN_LAST_NAME: str = "Administrator"

    # Storage
    STORAGE_BACKEND: str = "local" # local | s3
    LOCAL_STORAGE_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Notification Providers
    SMS_PROVIDER: str = "mock" # mock | twilio | msg91 | aws_sns
    EMAIL_PROVIDER: str = "mock" # mock | smtp | resend | brevo | sendgrid
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@votingplatform.org"
    RESEND_API_KEY: str = ""
    BREVO_API_KEY: str = ""
    SENDGRID_API_KEY: str = ""
    OTP_EXPIRE_MINUTES: int = 15
    OTP_MAX_ATTEMPTS: int = 5
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    TWILIO_WHATSAPP_FROM_NUMBER: str = ""

    WHATSAPP_PROVIDER: str = "mock" # mock | meta_cloud
    META_WHATSAPP_ACCESS_TOKEN: str = ""
    META_WHATSAPP_PHONE_NUMBER_ID: str = ""
    META_WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    META_WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "meta-webhook-verify-token-secret"
    META_WHATSAPP_APP_SECRET: str = ""

    INSTAGRAM_PROVIDER: str = "mock" # mock | meta_instagram
    META_INSTAGRAM_PAGE_ACCESS_TOKEN: str = ""
    META_INSTAGRAM_PAGE_ID: str = ""
    META_INSTAGRAM_APP_SECRET: str = ""

    # Webhook Secrets
    WEBHOOK_SECRET_SMS: str = "sms-webhook-secret-key"
    WEBHOOK_SECRET_WHATSAPP: str = "whatsapp-webhook-secret-key"
    WEBHOOK_SECRET_INSTAGRAM: str = "instagram-webhook-secret-key"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "sslmode=" in v:
                v = v.replace("sslmode=", "ssl=")
            if "-pooler." in v:
                v = v.replace("-pooler.", ".")
        return v

    @field_validator("DATABASE_SYNC_URL", mode="before")
    @classmethod
    def assemble_sync_db_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql://", 1)
            if v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql+asyncpg://", "postgresql://", 1)
            if "ssl=" in v and "sslmode=" not in v:
                v = v.replace("ssl=", "sslmode=")
            if "-pooler." in v:
                v = v.replace("-pooler.", ".")
        return v


settings = Settings()
