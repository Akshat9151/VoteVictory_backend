from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.task import CampaignTask, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Task Management"])


@router.get("", response_model=List[TaskResponse])
@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority_filter: Optional[TaskPriority] = Query(None, alias="priority"),
    mine: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all campaign tasks with optional status/priority filtering (Section 7.5)."""
    stmt = select(CampaignTask).options(
        selectinload(CampaignTask.assigned_to).selectinload(User.roles).selectinload(UserRole.role)
    )
    if not user_is_super_admin(current_user) and current_user.organization_id:
        stmt = stmt.where(CampaignTask.organization_id == current_user.organization_id)
    if _is_volunteer(current_user) or mine:
        stmt = stmt.where(CampaignTask.assigned_to_id == current_user.id)
    if status_filter:
        stmt = stmt.where(CampaignTask.status == status_filter)
    if priority_filter:
        stmt = stmt.where(CampaignTask.priority == priority_filter)
    stmt = stmt.order_by(desc(CampaignTask.created_at))

    result = await db.execute(stmt)
    return [_serialize_task(task) for task in result.scalars().all()]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
@router.post("/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(require_roles(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Create and assign a new field task to volunteer (Section 7.5)."""
    assignee = await _validate_assignee(task_in.assigned_to_id, current_user, db)
    task = CampaignTask(
        organization_id=current_user.organization_id,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        status=task_in.status,
        deadline=task_in.deadline,
        assigned_to_id=task_in.assigned_to_id,
        assigned_volunteer_name=_user_name(assignee) if assignee else task_in.assigned_volunteer_name,
        ward_or_booth=task_in.ward_or_booth,
        category=task_in.category,
    )
    db.add(task)
    await db.commit()
    task = (await db.execute(select(CampaignTask).options(
        selectinload(CampaignTask.assigned_to).selectinload(User.roles).selectinload(UserRole.role)
    ).where(CampaignTask.id == task.id))).scalars().one()
    return _serialize_task(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch task details by id."""
    stmt = select(CampaignTask).options(
        selectinload(CampaignTask.assigned_to).selectinload(User.roles).selectinload(UserRole.role)
    ).where(CampaignTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if _is_volunteer(current_user) and task.assigned_to_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this task")
    if not user_is_super_admin(current_user) and task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this task")
    return _serialize_task(task)


@router.put("/{task_id}", response_model=TaskResponse)
@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    update_in: TaskUpdate,
    current_user: User = Depends(require_roles(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Update task details."""
    stmt = select(CampaignTask).options(
        selectinload(CampaignTask.assigned_to).selectinload(User.roles).selectinload(UserRole.role)
    ).where(CampaignTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not user_is_super_admin(current_user) and task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this task")

    update_data = update_in.model_dump(exclude_unset=True)
    if "assigned_to_id" in update_data:
        assignee = await _validate_assignee(update_data["assigned_to_id"], current_user, db)
        update_data["assigned_volunteer_name"] = _user_name(assignee) if assignee else None
    for key, value in update_data.items():
        setattr(task, key, value)

    if task.status == TaskStatus.COMPLETED and not task.completed_at:
        task.completed_at = datetime.utcnow()

    await db.commit()
    task = (await db.execute(select(CampaignTask).options(
        selectinload(CampaignTask.assigned_to).selectinload(User.roles).selectinload(UserRole.role)
    ).where(CampaignTask.id == task.id))).scalars().one()
    return _serialize_task(task)


@router.put("/{task_id}/status", response_model=TaskResponse)
@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str,
    status_in: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task lifecycle status (Pending -> In Progress -> Completed)."""
    stmt = select(CampaignTask).options(
        selectinload(CampaignTask.assigned_to).selectinload(User.roles).selectinload(UserRole.role)
    ).where(CampaignTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not user_is_super_admin(current_user) and task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot update this task")
    if not (_is_admin(current_user) or task.assigned_to_id == current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assignee or an administrator can update this task")

    task.status = status_in.status
    if status_in.status == TaskStatus.COMPLETED:
        task.completed_at = datetime.utcnow()

    await db.commit()
    task = (await db.execute(select(CampaignTask).options(
        selectinload(CampaignTask.assigned_to).selectinload(User.roles).selectinload(UserRole.role)
    ).where(CampaignTask.id == task.id))).scalars().one()
    return _serialize_task(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: User = Depends(require_roles(["superadmin", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    stmt = select(CampaignTask).where(CampaignTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not user_is_super_admin(current_user) and task.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this task")

    await db.delete(task)
    await db.commit()
    return None


def _role_code(user: User) -> str:
    if user.is_superuser:
        return "SUPER_ADMIN"
    for link in user.roles or []:
        code = str(getattr(getattr(link, "role", None), "code", "")).upper()
        if code in {"SUPER_ADMIN", "ADMIN", "VOLUNTEER"}:
            return code
    return str(getattr(user, "role", "VOLUNTEER")).upper().replace(" ", "_")


def _is_admin(user: User) -> bool:
    return _role_code(user) in {"ADMIN", "SUPER_ADMIN"}


def user_is_super_admin(user: User) -> bool:
    return _role_code(user) == "SUPER_ADMIN"


def _is_volunteer(user: User) -> bool:
    return _role_code(user) == "VOLUNTEER"


def _user_name(user: Optional[User]) -> Optional[str]:
    return f"{user.first_name} {user.last_name}".strip() if user else None


async def _validate_assignee(assignee_id: Optional[str], current_user: User, db: AsyncSession) -> Optional[User]:
    if not assignee_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A task assignee is required")
    assignee = (await db.execute(select(User).options(
        selectinload(User.roles).selectinload(UserRole.role)
    ).where(User.id == assignee_id, User.is_active.is_(True)))).scalars().first()
    if not assignee:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assigned user does not exist or is inactive")
    assignee_role = _role_code(assignee)
    if assignee_role == "SUPER_ADMIN" or (_role_code(current_user) == "ADMIN" and assignee_role != "VOLUNTEER"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot assign tasks to this role")
    return assignee


def _serialize_task(task: CampaignTask) -> TaskResponse:
    response = TaskResponse.model_validate(task)
    response.assigned_to_name = _user_name(task.assigned_to)
    response.assigned_to_role = _role_code(task.assigned_to) if task.assigned_to else None
    response.assigned_volunteer_name = response.assigned_to_name or task.assigned_volunteer_name
    return response
