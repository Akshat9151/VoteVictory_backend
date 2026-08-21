import uuid
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

class PosterShare(BaseModel):
    __tablename__ = "poster_shares"

    poster_id = Column(String(36), ForeignKey("saved_designs.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)

    poster = relationship("SavedDesign", backref="shares")
    shared_by = relationship("User", foreign_keys=[shared_by_user_id])
    shared_with = relationship("User", foreign_keys=[shared_with_user_id])
