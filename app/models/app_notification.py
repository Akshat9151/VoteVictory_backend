import uuid
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

class AppNotification(BaseModel):
    __tablename__ = "app_notifications"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    related_poster_id = Column(String(36), ForeignKey("saved_designs.id", ondelete="CASCADE"), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="app_notifications")
    related_poster = relationship("SavedDesign")
