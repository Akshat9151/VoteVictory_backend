from typing import Any, Dict, Optional

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
    organization_id: str
    user_id: Optional[str] = None

    class Config:
        from_attributes = True