from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.task import TaskPriority, TaskStatus


def _parse_priority(v):
    if isinstance(v, str):
        clean = v.strip().lower()
        if clean in ["urgent", "high", "medium", "low"]:
            return TaskPriority(clean)
    return v


def _parse_status(v):
    if isinstance(v, str):
        clean = v.strip().lower()
        if clean in ["in_progress", "in-progress", "in progress"]:
            return TaskStatus.IN_PROGRESS
        if clean in ["completed", "done", "finished"]:
            return TaskStatus.COMPLETED
        if clean in ["pending", "todo"]:
            return TaskStatus.PENDING
    return v


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Union[TaskPriority, str] = TaskPriority.HIGH
    status: Union[TaskStatus, str] = TaskStatus.PENDING
    deadline: Optional[str] = None
    assigned_to_id: Optional[str] = None
    assigned_volunteer_name: Optional[str] = None
    ward_or_booth: Optional[str] = None
    category: Optional[str] = "Voter Contact"

    @field_validator("priority", mode="before")
    @classmethod
    def parse_pri(cls, v):
        return _parse_priority(v)

    @field_validator("status", mode="before")
    @classmethod
    def parse_stat(cls, v):
        return _parse_status(v)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Union[TaskPriority, str]] = None
    status: Optional[Union[TaskStatus, str]] = None
    deadline: Optional[str] = None
    assigned_to_id: Optional[str] = None
    assigned_volunteer_name: Optional[str] = None
    ward_or_booth: Optional[str] = None
    category: Optional[str] = None

    @field_validator("priority", mode="before")
    @classmethod
    def parse_pri(cls, v):
        return _parse_priority(v)

    @field_validator("status", mode="before")
    @classmethod
    def parse_stat(cls, v):
        return _parse_status(v)


class TaskStatusUpdate(BaseModel):
    status: Union[TaskStatus, str]

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v):
        return _parse_status(v)


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    status: TaskStatus
    deadline: Optional[str] = None
    assigned_to_id: Optional[str] = None
    assigned_volunteer_name: Optional[str] = None
    ward_or_booth: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
