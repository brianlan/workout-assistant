"""Tests for the Plan API endpoints."""

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Category, Plan, PlanItem, Video


def _create_category_and_videos(client: TestClient, engine):
    """Create a category and some videos for plan tests."""
    cat_resp = client.post("/api/categories", json={"name": "Strength"})
    cat_id = cat_resp.json()["id"]

    video_ids = []
    with Session(engine) as session:
        for i in range(3):
            v = Video(
                title=f"Video {i + 1}",
                category_id=cat_id,
                difficulty=["beginner", "intermediate", "advanced"][i % 3],
                muscle_groups=json.dumps([f"muscle_{i}"]),
                duration=100.0 * (i + 1),
                file_path=f"/data/videos/test/v{i + 1}.mp4",
                status="ready",
            )
            session.add(v)
        session.commit()
        # Fetch all to get their IDs
        all_vids = session.exec(
            select(Video).where(Video.category_id == cat_id)
        ).all()
        video_ids = [v.id for v in all_vids]

    return cat_id, video_ids


def _write_test_config(tmp_path):
    """Write a test AI config file."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "base_url": "https://api.example.com/v1",
        "api_key": "test-key",
        "model_name": "gpt-4",
    }))
    return config_path


class TestPlanGenerate:
    """POST /api/plans/generate"""

    @patch("app.routers.plans.call_llm")
    def test_generate_plan_with_mocked_llm(self, mock_call_llm, client, engine, tmp_path):
        """Generate a plan with a mocked LLM response."""
        cat_id, video_ids = _create_category_and_videos(client, engine)
        _write_test_config(tmp_path)

        mock_call_llm.return_value = json.dumps({
            "title": "3-Day Strength Plan",
            "plan_type": "weekly",
            "items": [
                {"video_id": video_ids[0], "day_position": 1, "order_position": 1},
                {"video_id": video_ids[1], "day_position": 2, "order_position": 1},
                {"video_id": video_ids[2], "day_position": 3, "order_position": 1},
            ],
        })

        response = client.post(
            "/api/plans/generate",
            json={
                "plan_type": "weekly",
                "focus_areas": ["strength"],
                "days_per_week": 3,
            },
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["title"] == "3-Day Strength Plan"
        assert data["plan_type"] == "weekly"
        assert len(data["items"]) == 3
        assert data["items"][0]["video_id"] == video_ids[0]

    @patch("app.routers.plans.call_llm")
    def test_generate_plan_with_parameters(self, mock_call_llm, client, engine, tmp_path):
        """Generate a plan with all parameters."""
        cat_id, video_ids = _create_category_and_videos(client, engine)
        _write_test_config(tmp_path)

        mock_call_llm.return_value = json.dumps({
            "title": "Custom Plan",
            "plan_type": "multi_week",
            "items": [
                {"video_id": video_ids[0], "day_position": 1, "order_position": 1},
            ],
        })

        response = client.post(
            "/api/plans/generate",
            json={
                "plan_type": "multi_week",
                "focus_areas": ["chest", "back"],
                "days_per_week": 4,
                "duration_weeks": 2,
            },
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["title"] == "Custom Plan"

    def test_generate_plan_no_videos(self, client, tmp_path):
        """Generating a plan with no videos should fail."""
        _write_test_config(tmp_path)
        response = client.post(
            "/api/plans/generate",
            json={
                "plan_type": "weekly",
                "days_per_week": 3,
            },
        )
        # Should return error since no videos to reference
        assert response.status_code in (400, 422)

    @patch("app.routers.plans.call_llm")
    def test_generate_plan_llm_error(self, mock_call_llm, client, engine, tmp_path):
        """Handle LLM errors gracefully."""
        cat_id, video_ids = _create_category_and_videos(client, engine)
        _write_test_config(tmp_path)

        from app.services.ai_planner import AIServerError
        mock_call_llm.side_effect = AIServerError("LLM API server error (500)")

        response = client.post(
            "/api/plans/generate",
            json={
                "plan_type": "weekly",
                "days_per_week": 3,
            },
        )

        assert response.status_code == 502


class TestListPlans:
    """GET /api/plans"""

    def test_list_plans_empty(self, client):
        response = client.get("/api/plans")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_plans(self, client, engine):
        with Session(engine) as session:
            for i in range(3):
                plan = Plan(
                    title=f"Plan {i + 1}",
                    plan_type="weekly",
                    parameters=json.dumps({"days_per_week": 3}),
                )
                session.add(plan)
            session.commit()

        response = client.get("/api/plans")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestGetPlan:
    """GET /api/plans/{id}"""

    def test_get_plan_with_items(self, client, engine):
        cat_id, video_ids = _create_category_and_videos(client, engine)

        plan_id = None
        with Session(engine) as session:
            plan = Plan(
                title="Test Plan",
                plan_type="weekly",
                parameters=json.dumps({"days_per_week": 2}),
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
            plan_id = plan.id

            item1 = PlanItem(
                plan_id=plan_id,
                video_id=video_ids[0],
                day_position=1,
                order_position=1,
            )
            item2 = PlanItem(
                plan_id=plan_id,
                video_id=video_ids[1],
                day_position=2,
                order_position=1,
            )
            session.add(item1)
            session.add(item2)
            session.commit()

        response = client.get(f"/api/plans/{plan_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Plan"
        assert len(data["items"]) == 2

    def test_get_plan_not_found(self, client):
        response = client.get("/api/plans/999")
        assert response.status_code == 404


class TestPlanCompletion:
    """PATCH /api/plans/{id}/items/{item_id}"""

    def test_toggle_item_complete(self, client, engine):
        cat_id, video_ids = _create_category_and_videos(client, engine)

        plan_id = None
        item_id = None
        with Session(engine) as session:
            plan = Plan(
                title="Toggle Test",
                plan_type="single_session",
                parameters="{}",
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
            plan_id = plan.id

            item = PlanItem(
                plan_id=plan_id,
                video_id=video_ids[0],
                day_position=1,
                order_position=1,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            item_id = item.id

        response = client.patch(
            f"/api/plans/{plan_id}/items/{item_id}",
            json={"completed": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True
        assert data["completed_at"] is not None

    def test_toggle_item_incomplete(self, client, engine):
        cat_id, video_ids = _create_category_and_videos(client, engine)

        plan_id = None
        item_id = None
        with Session(engine) as session:
            plan = Plan(
                title="Uncomplete Test",
                plan_type="single_session",
                parameters="{}",
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
            plan_id = plan.id

            item = PlanItem(
                plan_id=plan_id,
                video_id=video_ids[0],
                day_position=1,
                order_position=1,
                completed=True,
                completed_at=datetime.now(),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            item_id = item.id

        response = client.patch(
            f"/api/plans/{plan_id}/items/{item_id}",
            json={"completed": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is False
        assert data["completed_at"] is None


class TestPlanRegenerate:
    """POST /api/plans/{id}/regenerate"""

    @patch("app.routers.plans.call_llm")
    def test_regenerate_plan(self, mock_call_llm, client, engine, tmp_path):
        cat_id, video_ids = _create_category_and_videos(client, engine)
        _write_test_config(tmp_path)

        mock_call_llm.return_value = json.dumps({
            "title": "New Plan",
            "plan_type": "weekly",
            "items": [
                {"video_id": video_ids[0], "day_position": 1, "order_position": 1},
                {"video_id": video_ids[2], "day_position": 2, "order_position": 1},
            ],
        })

        # Create original plan
        plan_id = None
        with Session(engine) as session:
            plan = Plan(
                title="Old Plan",
                plan_type="weekly",
                parameters=json.dumps({"days_per_week": 3}),
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
            plan_id = plan.id

        response = client.post(f"/api/plans/{plan_id}/regenerate")
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Plan"
        assert len(data["items"]) == 2


class TestPlanHistory:
    """GET /api/plans/history"""

    def test_history_with_completion(self, client, engine):
        cat_id, video_ids = _create_category_and_videos(client, engine)

        plan_id = None
        with Session(engine) as session:
            plan = Plan(
                title="History Plan",
                plan_type="weekly",
                parameters="{}",
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
            plan_id = plan.id

            # One complete, one incomplete item
            item1 = PlanItem(
                plan_id=plan_id,
                video_id=video_ids[0],
                day_position=1,
                order_position=1,
                completed=True,
                completed_at=datetime.now(),
            )
            item2 = PlanItem(
                plan_id=plan_id,
                video_id=video_ids[1],
                day_position=2,
                order_position=1,
                completed=False,
            )
            session.add(item1)
            session.add(item2)
            session.commit()

        response = client.get("/api/plans/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        # Find our plan in the history
        our_plan = next(p for p in data if p["id"] == plan_id)
        assert our_plan["completion_pct"] == 50.0


class TestPlanStats:
    """GET /api/plans/stats"""

    def test_stats(self, client, engine):
        cat_id, video_ids = _create_category_and_videos(client, engine)

        with Session(engine) as session:
            plan = Plan(
                title="Stats Plan",
                plan_type="weekly",
                parameters="{}",
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
            plan_id = plan.id

            item = PlanItem(
                plan_id=plan_id,
                video_id=video_ids[0],
                day_position=1,
                order_position=1,
                completed=True,
                completed_at=datetime.now(),
            )
            session.add(item)
            session.commit()

        response = client.get("/api/plans/stats")
        assert response.status_code == 200
        data = response.json()
        assert "completion_rate" in data
        assert "category_breakdown" in data
