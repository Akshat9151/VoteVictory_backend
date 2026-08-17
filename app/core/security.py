import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
import jwt
from passlib.context import CryptContext
import pyotp
from app.core.config import settings

# Password hashing context with Argon2id primary and Bcrypt fallback
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__type="ID", # Argon2id
    argon2__memory_cost=65536, # 64MB
    argon2__time_cost=3,
    argon2__parallelism=4
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verify plain password against argon2/bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate Argon2id secure password hash."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    organization_id: Optional[str] = None,
    role: str = "VOLUNTEER",
    permissions: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create short-lived JWT access token with user claims and permissions."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "org_id": str(organization_id) if organization_id else None,
        "role": role,
        "permissions": permissions or [],
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "nbf": datetime.now(timezone.utc),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> tuple[str, str]:
    """
    Create a long-lived cryptographic refresh token.
    Returns (raw_token, token_hash) to store hash securely in database.
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a token for secure database storage/lookups."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]}
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def generate_totp_secret() -> str:
    """Generate base32 secret for TOTP authentication."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer_name: str = "ElectWin") -> str:
    """Generate TOTP provisioning URI for QR code scanning."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer_name)


def verify_totp(secret: str, code: str) -> bool:
    """Verify 6-digit TOTP code against secret with 1-step window tolerance."""
    if not secret or not code:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code.strip(), valid_window=1)
    except Exception:
        return False


def generate_secure_otp(length: int = 6) -> str:
    """Generate cryptographically secure numeric OTP."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def generate_ballot_nonce() -> str:
    """Generate anonymous cryptographic nonce for ballot serial hash."""
    return secrets.token_hex(32)


def compute_ballot_hash(election_id: str, nonce: str) -> str:
    """Generate verifiable SHA-256 ballot serial hash."""
    msg = f"{election_id}:{nonce}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def generate_recovery_codes(count: int = 8) -> List[str]:
    """Generate one-time account recovery backup codes."""
    codes = []
    for _ in range(count):
        code = f"{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
        codes.append(code)
    return codes
