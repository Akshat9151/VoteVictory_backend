import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String, Text

from app.models.base import BaseModel


class SecuritySeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditLog(BaseModel):
    """
    Immutable, append-only operational audit log.
    Strictly forbids update and delete queries for compliance.
    """
    __tablename__ = "audit_logs"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=True)

    action = Column(String(100), nullable=False, index=True) # e.g. "auth.login", "election.create", "voter.checkin"
    resource_type = Column(String(100), nullable=False, index=True) # e.g. "election", "voter", "candidate"
    resource_id = Column(String(100), nullable=True, index=True)

    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True, index=True)

    prev_state_json = Column(Text, nullable=True)
    new_state_json = Column(Text, nullable=True)
    is_success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)


class SecurityEvent(BaseModel):
    """Real-time security anomaly and intrusion monitoring record."""
    __tablename__ = "security_events"

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    event_type = Column(String(100), nullable=False, index=True) # FAILED_LOGIN, BRUTE_FORCE, UNAUTHORIZED_ACCESS, TOKEN_ABUSE, SUSPICIOUS_VOTING, RATE_LIMIT_EXCEEDED
    severity = Column(Enum(SecuritySeverity), default=SecuritySeverity.LOW, nullable=False, index=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
