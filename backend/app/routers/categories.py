"""Category CRUD API router."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.database import get_session
from app.models import Category, Video

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()


class CategoryUpdate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()


class CategoryRead(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=CategoryRead, status_code=201)
def create_category(
    data: CategoryCreate,
    session: Session = Depends(get_session),
):
    """Create a new category."""
    existing = session.exec(
        select(Category).where(Category.name == data.name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Category name already exists")

    category = Category(name=data.name)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.get("", response_model=list[CategoryRead])
def list_categories(
    session: Session = Depends(get_session),
):
    """List all categories."""
    categories = session.exec(select(Category)).all()
    return categories


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    session: Session = Depends(get_session),
):
    """Get a single category by ID."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    session: Session = Depends(get_session),
):
    """Update a category's name."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    existing = session.exec(
        select(Category).where(Category.name == data.name)
    ).first()
    if existing and existing.id != category_id:
        raise HTTPException(status_code=409, detail="Category name already exists")

    category.name = data.name
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    reassign_to: int | None = Query(None),
    session: Session = Depends(get_session),
):
    """Delete a category. Optionally reassign videos to another category."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Find videos in this category
    videos = session.exec(
        select(Video).where(Video.category_id == category_id)
    ).all()

    if videos:
        if reassign_to is not None:
            target = session.get(Category, reassign_to)
            if not target:
                raise HTTPException(
                    status_code=400,
                    detail="Reassignment target category not found",
                )
            for video in videos:
                video.category_id = reassign_to
                session.add(video)
        else:
            raise HTTPException(
                status_code=400,
                detail="Category has videos. Specify reassign_to parameter.",
            )

    session.delete(category)
    session.commit()
    return None
