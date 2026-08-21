from typing import Any, Dict, Optional
from datetime import datetime

from pydantic import BaseModel


class SavedDesignCreate(BaseModel):
    template_id: str
    election_id: Optional[str] = None
    title: str
    form_data: Dict[str, Any]
    preview_image_url: Optional[str] = None
    canvas_json: Optional[Dict[str, Any]] = None


class SavedDesignResponse(SavedDesignCreate):
    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True