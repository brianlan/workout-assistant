"""SQLModel database models."""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)


class Video(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str | None = None
    category_id: int = Field(foreign_key="category.id")
    difficulty: str | None = None  # beginner/intermediate/advanced
    muscle_groups: str | None = None  # JSON list
    duration: float | None = None  # seconds
    format: str | None = None
    file_size: int | None = None  # bytes
    thumbnail_path: str | None = None
    file_path: str
    source_url: str | None = None
    status: str = "importing"  # importing/transcoding/ready/failed
    imported_at: datetime = Field(default_factory=datetime.now)


class Plan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    plan_type: str  # single_session/weekly/multi_week
    parameters: str  # JSON: focus_areas, days_per_week, duration_weeks
    created_at: datetime = Field(default_factory=datetime.now)


class PlanItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="plan.id")
    video_id: int | None = Field(default=None, foreign_key="video.id")
    day_position: int
    order_position: int
    completed: bool = False
    completed_at: datetime | None = None
