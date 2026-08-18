from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.HIGH
    status: TaskStatus = TaskStatus.PENDING
    deadline: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    assigned_volunteer_name: Optional[str] = None
    ward_or_booth: Optional[str] = None
    category: Optional[str] = "Voter Contact"


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    status: TaskStatus
    deadline: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    assigned_volunteer_name: Optional[str] = None
    ward_or_booth: Optional[str] = None
    category: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
