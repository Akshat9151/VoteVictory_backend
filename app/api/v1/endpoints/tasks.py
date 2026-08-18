from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.task import CampaignTask, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate

router = APIRouter(prefix="/tasks", tags=["Task Management"])


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority_filter: Optional[TaskPriority] = Query(None, alias="priority"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all campaign tasks with optional status/priority filtering (Section 7.5)."""
    stmt = select(CampaignTask)
    if status_filter:
        stmt = stmt.where(CampaignTask.status == status_filter)
    if priority_filter:
        stmt = stmt.where(CampaignTask.priority == priority_filter)
    stmt = stmt.order_by(desc(CampaignTask.created_at))
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create and assign a new field task to volunteer (Section 7.5)."""
    task = CampaignTask(
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        status=task_in.status,
        deadline=task_in.deadline,
        assigned_to_id=task_in.assigned_to_id,
        assigned_volunteer_name=task_in.assigned_volunteer_name,
        ward_or_booth=task_in.ward_or_booth,
        category=task_in.category,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: UUID,
    status_in: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update task lifecycle status (Pending -> In Progress -> Completed)."""
    stmt = select(CampaignTask).where(CampaignTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    task.status = status_in.status
    if status_in.status == TaskStatus.COMPLETED:
        task.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    return task
