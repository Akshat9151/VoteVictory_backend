import math
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import BaseModel
from app.schemas.common import PaginationMeta

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: str, organization_id: Optional[str] = None) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        if organization_id and hasattr(self.model, "organization_id"):
            stmt = stmt.where(self.model.organization_id == organization_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        organization_id: Optional[str] = None,
        limit: Optional[int] = None,
        order_by: Optional[Any] = None
    ) -> List[ModelType]:
        stmt = select(self.model)
        if organization_id and hasattr(self.model, "organization_id"):
            stmt = stmt.where(self.model.organization_id == organization_id)
        if filters:
            for field, val in filters.items():
                if val is not None and hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == val)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        search_query: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        order_by: Optional[Any] = None
    ) -> Tuple[List[ModelType], PaginationMeta]:
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        if filters:
            for field, val in filters.items():
                if val is not None and hasattr(self.model, field):
                    column = getattr(self.model, field)
                    stmt = stmt.where(column == val)
                    count_stmt = count_stmt.where(column == val)

        if search_query and search_fields:
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    search_conditions.append(column.ilike(f"%{search_query}%"))
            if search_conditions:
                from sqlalchemy import or_
                stmt = stmt.where(or_(*search_conditions))
                count_stmt = count_stmt.where(or_(*search_conditions))

        # Get total count
        total_res = await self.db.execute(count_stmt)
        total_items = total_res.scalar_one()

        # Ordering & Pagination
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model.created_at.desc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        total_pages = max(1, math.ceil(total_items / page_size))

        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        return items, pagination

    async def create(self, entity: ModelType) -> ModelType:
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity: ModelType) -> None:
        await self.db.delete(entity)
        await self.db.flush()
