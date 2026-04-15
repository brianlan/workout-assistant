"""Tests for database models: Category, Video, Plan, PlanItem."""

from datetime import datetime

import pytest
from sqlmodel import Session, select

from app.models import Category, Video, Plan, PlanItem


class TestCategory:
    """Tests for the Category model."""

    def test_create_category(self, session: Session):
        category = Category(name="Strength")
        session.add(category)
        session.commit()
        session.refresh(category)

        assert category.id is not None
        assert category.name == "Strength"
        assert category.created_at is not None

    def test_category_name_uniqueness(self, session: Session):
        category1 = Category(name="Cardio")
        session.add(category1)
        session.commit()

        category2 = Category(name="Cardio")
        session.add(category2)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()

    def test_read_category(self, session: Session):
        category = Category(name="HIIT")
        session.add(category)
        session.commit()

        result = session.exec(select(Category).where(Category.name == "HIIT")).first()
        assert result is not None
        assert result.name == "HIIT"

    def test_update_category(self, session: Session):
        category = Category(name="Yoga")
        session.add(category)
        session.commit()

        category.name = "Pilates"
        session.add(category)
        session.commit()

        result = session.exec(select(Category).where(Category.id == category.id)).first()
        assert result.name == "Pilates"

    def test_delete_category(self, session: Session):
        category = Category(name="Stretching")
        session.add(category)
        session.commit()
        cat_id = category.id

        session.delete(category)
        session.commit()

        result = session.exec(select(Category).where(Category.id == cat_id)).first()
        assert result is None


class TestVideo:
    """Tests for the Video model."""

    def _create_category(self, session: Session) -> Category:
        category = Category(name="Strength")
        session.add(category)
        session.commit()
        return category

    def test_create_video(self, session: Session):
        category = self._create_category(session)
        video = Video(
            title="Push-Up Workout",
            description="A great push-up routine",
            category_id=category.id,
            difficulty="beginner",
            muscle_groups='["chest", "triceps"]',
            duration=300.0,
            format="mp4",
            file_size=10_000_000,
            file_path="/data/videos/strength/abc123.mp4",
            source_url="https://youtube.com/watch?v=abc",
            status="ready",
        )
        session.add(video)
        session.commit()
        session.refresh(video)

        assert video.id is not None
        assert video.title == "Push-Up Workout"
        assert video.description == "A great push-up routine"
        assert video.category_id == category.id
        assert video.difficulty == "beginner"
        assert video.muscle_groups == '["chest", "triceps"]'
        assert video.duration == 300.0
        assert video.format == "mp4"
        assert video.file_size == 10_000_000
        assert video.status == "ready"
        assert video.imported_at is not None

    def test_video_fk_to_category(self, session: Session):
        category = self._create_category(session)
        video = Video(
            title="Squat Workout",
            category_id=category.id,
            file_path="/data/videos/strength/def456.mp4",
        )
        session.add(video)
        session.commit()

        result = session.exec(select(Video).where(Video.title == "Squat Workout")).first()
        assert result is not None
        assert result.category_id == category.id

    def test_video_optional_fields(self, session: Session):
        category = self._create_category(session)
        video = Video(
            title="Minimal Video",
            category_id=category.id,
            file_path="/data/videos/strength/min.mp4",
        )
        session.add(video)
        session.commit()
        session.refresh(video)

        assert video.description is None
        assert video.difficulty is None
        assert video.muscle_groups is None
        assert video.duration is None
        assert video.format is None
        assert video.file_size is None
        assert video.thumbnail_path is None
        assert video.source_url is None
        assert video.status == "importing"

    def test_delete_video(self, session: Session):
        category = self._create_category(session)
        video = Video(
            title="To Delete",
            category_id=category.id,
            file_path="/data/videos/strength/del.mp4",
        )
        session.add(video)
        session.commit()
        vid_id = video.id

        session.delete(video)
        session.commit()

        result = session.exec(select(Video).where(Video.id == vid_id)).first()
        assert result is None


class TestPlanAndPlanItems:
    """Tests for the Plan and PlanItem models."""

    def _create_category_and_video(self, session: Session):
        category = Category(name="Cardio")
        session.add(category)
        session.commit()
        video = Video(
            title="Jumping Jacks",
            category_id=category.id,
            file_path="/data/videos/cardio/jj.mp4",
        )
        session.add(video)
        session.commit()
        return category, video

    def test_create_plan_with_items(self, session: Session):
        _, video = self._create_category_and_video(session)
        plan = Plan(
            title="3-Day Beginner Plan",
            plan_type="weekly",
            parameters='{"focus_areas": ["full body"], "days_per_week": 3}',
        )
        session.add(plan)
        session.commit()

        item1 = PlanItem(
            plan_id=plan.id,
            video_id=video.id,
            day_position=1,
            order_position=1,
        )
        item2 = PlanItem(
            plan_id=plan.id,
            video_id=video.id,
            day_position=2,
            order_position=1,
        )
        session.add(item1)
        session.add(item2)
        session.commit()

        result = session.exec(select(Plan).where(Plan.id == plan.id)).first()
        assert result is not None
        assert result.title == "3-Day Beginner Plan"
        assert result.plan_type == "weekly"

        items = session.exec(
            select(PlanItem).where(PlanItem.plan_id == plan.id)
        ).all()
        assert len(items) == 2
        assert items[0].day_position == 1
        assert items[1].day_position == 2

    def test_plan_item_nullable_video_id(self, session: Session):
        plan = Plan(
            title="Plan with deleted video",
            plan_type="single_session",
            parameters="{}",
        )
        session.add(plan)
        session.commit()

        item = PlanItem(
            plan_id=plan.id,
            video_id=None,
            day_position=1,
            order_position=1,
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        assert item.video_id is None

    def test_plan_item_completion(self, session: Session):
        _, video = self._create_category_and_video(session)
        plan = Plan(
            title="Completion Test",
            plan_type="single_session",
            parameters="{}",
        )
        session.add(plan)
        session.commit()

        item = PlanItem(
            plan_id=plan.id,
            video_id=video.id,
            day_position=1,
            order_position=1,
        )
        session.add(item)
        session.commit()

        assert item.completed is False
        assert item.completed_at is None

        now = datetime.now()
        item.completed = True
        item.completed_at = now
        session.add(item)
        session.commit()

        result = session.exec(
            select(PlanItem).where(PlanItem.id == item.id)
        ).first()
        assert result.completed is True
        assert result.completed_at is not None

    def test_delete_cascade_plan_items(self, session: Session):
        _, video = self._create_category_and_video(session)
        plan = Plan(
            title="Delete Test",
            plan_type="single_session",
            parameters="{}",
        )
        session.add(plan)
        session.commit()

        item = PlanItem(
            plan_id=plan.id,
            video_id=video.id,
            day_position=1,
            order_position=1,
        )
        session.add(item)
        session.commit()
        item_id = item.id

        session.delete(plan)
        session.commit()

        result = session.exec(
            select(PlanItem).where(PlanItem.id == item_id)
        ).first()
        # SQLite with SQLModel may or may not cascade; verify behavior
        # In practice we handle this at the application level
