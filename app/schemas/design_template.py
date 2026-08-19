import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator


class TemplateElement(BaseModel):
    type: str  # text, image, shape, symbol, photo
    x: float
    y: float
    width: float
    height: float
    placeholder: Optional[str] = None
    value: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[str] = None
    color: Optional[str] = None
    bg_color: Optional[str] = None
    border_color: Optional[str] = None
    border_width: Optional[float] = None
    border_radius: Optional[float] = None
    text_align: Optional[str] = None
    z_index: int = 1


class TemplateLayoutJson(BaseModel):
    bg_color: str = "#ffffff"
    width: int = 600
    height: int = 848
    elements: List[TemplateElement] = []


class DesignTemplateCreate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    election_type: Optional[str] = "panchayat"
    category: str = "poster"
    format_name: Optional[str] = None
    format_dims: Optional[str] = None
    layout_json: Optional[Union[Dict[str, Any], str]] = Field(default_factory=dict)
    canvas_json: Optional[Union[Dict[str, Any], str]] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: bool = True
    display_order: int = 1

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, values: Any):
        if isinstance(values, dict):
            if not values.get("name") and values.get("title"):
                values["name"] = values["title"]
            if not values.get("layout_json") and values.get("canvas_json"):
                values["layout_json"] = values["canvas_json"]
            if isinstance(values.get("layout_json"), str):
                try:
                    values["layout_json"] = json.loads(values["layout_json"])
                except Exception:
                    values["layout_json"] = {"raw": values["layout_json"]}
        return values


class DesignTemplateUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    election_type: Optional[str] = None
    category: Optional[str] = None
    format_name: Optional[str] = None
    format_dims: Optional[str] = None
    layout_json: Optional[Union[Dict[str, Any], str]] = None
    canvas_json: Optional[Union[Dict[str, Any], str]] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, values: Any):
        if isinstance(values, dict):
            if not values.get("name") and values.get("title"):
                values["name"] = values["title"]
            if not values.get("layout_json") and values.get("canvas_json"):
                values["layout_json"] = values["canvas_json"]
            if isinstance(values.get("layout_json"), str):
                try:
                    values["layout_json"] = json.loads(values["layout_json"])
                except Exception:
                    values["layout_json"] = {"raw": values["layout_json"]}
        return values


class DesignTemplateResponse(BaseModel):
    id: str
    organization_id: Optional[str] = None
    name: str
    title: Optional[str] = None
    election_type: Optional[str] = None
    category: str
    format_name: Optional[str] = None
    format_dims: Optional[str] = None
    layout_json: Dict[str, Any] = {}
    canvas_json: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: bool = True
    display_order: int = 1
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, values: Any):
        if hasattr(values, "name") and not hasattr(values, "title"):
            setattr(values, "title", values.name)
        elif isinstance(values, dict) and "name" in values and "title" not in values:
            values["title"] = values["name"]
        return values

    class Config:
        from_attributes = True
