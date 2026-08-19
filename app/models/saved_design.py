import uuid

from sqlalchemy import Column, ForeignKey, JSON, String, Text

from app.models.base import BaseModel


class SavedDesign(BaseModel):
    __tablename__ = "saved_designs"

    organization_id = Column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    election_id = Column(String(64), ForeignKey("elections.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(String(64), ForeignKey("design_templates.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    form_data = Column(JSON, nullable=False, default=dict)
    canvas_json = Column(JSON, nullable=True)
    preview_image_url = Column(Text, nullable=True)
