"""Tests for the AI planner service."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.models import Category, Video
from app.services.ai_planner import (
    AIClientError,
    AIAuthError,
    AIServerError,
    ParseError,
    build_prompt,
    call_llm,
    parse_response,
)


def _make_video(
    id: int,
    title: str = "Test Video",
    category: str = "Strength",
    difficulty: str = "intermediate",
    duration: float = 300.0,
    muscle_groups: str = '["chest"]',
) -> Video:
    """Create a mock Video object for testing."""
    video = Video(
        id=id,
        title=title,
        description="A test video",
        category_id=1,
        difficulty=difficulty,
        muscle_groups=muscle_groups,
        duration=duration,
        format="mp4",
        file_size=1000000,
        file_path=f"/data/videos/{category.lower()}/test{id}.mp4",
        status="ready",
        imported_at=datetime.now(),
    )
    return video


def _make_video_list(count: int = 3) -> list[Video]:
    """Create a list of mock Video objects."""
    videos = []
    categories = ["Strength", "Cardio", "HIIT"]
    difficulties = ["beginner", "intermediate", "advanced"]
    for i in range(count):
        v = _make_video(
            id=i + 1,
            title=f"Video {i + 1}",
            category=categories[i % len(categories)],
            difficulty=difficulties[i % len(difficulties)],
            duration=100.0 * (i + 1),
            muscle_groups=json.dumps([f"muscle_{i}"]),
        )
        videos.append(v)
    return videos


class TestBuildPrompt:
    """Tests for the prompt builder."""

    def test_prompt_includes_system_role(self):
        videos = _make_video_list()
        params = {
            "plan_type": "weekly",
            "focus_areas": ["chest", "back"],
            "days_per_week": 3,
        }
        messages = build_prompt(videos, params)
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert "workout" in messages[0]["content"].lower()

    def test_prompt_includes_video_library(self):
        videos = _make_video_list(3)
        params = {"plan_type": "single_session"}
        messages = build_prompt(videos, params)
        combined = json.dumps(messages)
        # Check that video info is included
        for v in videos:
            assert v.title in combined
            assert str(v.id) in combined

    def test_prompt_includes_user_parameters(self):
        videos = _make_video_list()
        params = {
            "plan_type": "weekly",
            "focus_areas": ["legs"],
            "days_per_week": 4,
            "duration_weeks": 2,
        }
        messages = build_prompt(videos, params)
        user_msg = messages[-1]["content"]
        assert "weekly" in user_msg.lower()
        assert "legs" in user_msg.lower()
        assert "4" in user_msg

    def test_prompt_includes_output_format(self):
        videos = _make_video_list()
        params = {"plan_type": "single_session"}
        messages = build_prompt(videos, params)
        combined = json.dumps(messages)
        assert "json" in combined.lower()
        assert "video_id" in combined.lower()

    def test_prompt_includes_category_and_difficulty(self):
        videos = _make_video_list()
        params = {"plan_type": "single_session"}
        messages = build_prompt(videos, params)
        combined = json.dumps(messages)
        assert "category" in combined.lower()
        assert "difficulty" in combined.lower()

    def test_prompt_empty_library(self):
        params = {"plan_type": "single_session"}
        messages = build_prompt([], params)
        assert len(messages) >= 2
        # Should still include system message and output format


class TestParseResponse:
    """Tests for the LLM response parser."""

    def test_parse_valid_response(self):
        valid_video_ids = {1, 2, 3}
        response_text = json.dumps({
            "title": "Weekly Plan",
            "plan_type": "weekly",
            "items": [
                {"video_id": 1, "day_position": 1, "order_position": 1},
                {"video_id": 2, "day_position": 1, "order_position": 2},
                {"video_id": 3, "day_position": 2, "order_position": 1},
            ],
        })
        plan_data, items = parse_response(response_text, valid_video_ids)
        assert plan_data["title"] == "Weekly Plan"
        assert plan_data["plan_type"] == "weekly"
        assert len(items) == 3
        assert items[0]["video_id"] == 1
        assert items[0]["day_position"] == 1

    def test_parse_malformed_json(self):
        valid_video_ids = {1, 2}
        with pytest.raises(ParseError, match="JSON"):
            parse_response("not valid json{{{", valid_video_ids)

    def test_parse_missing_fields(self):
        valid_video_ids = {1, 2}
        response_text = json.dumps({"items": []})
        with pytest.raises(ParseError, match="title"):
            parse_response(response_text, valid_video_ids)

    def test_parse_invalid_video_ids(self):
        valid_video_ids = {1, 2}
        response_text = json.dumps({
            "title": "Bad Plan",
            "plan_type": "weekly",
            "items": [
                {"video_id": 999, "day_position": 1, "order_position": 1},
            ],
        })
        with pytest.raises(ParseError, match="999"):
            parse_response(response_text, valid_video_ids)

    def test_parse_empty_items(self):
        valid_video_ids = {1, 2}
        response_text = json.dumps({
            "title": "Empty Plan",
            "plan_type": "single_session",
            "items": [],
        })
        plan_data, items = parse_response(response_text, valid_video_ids)
        assert len(items) == 0

    def test_parse_response_wrapped_in_markdown(self):
        """LLM responses sometimes come wrapped in markdown code blocks."""
        valid_video_ids = {1, 2}
        inner = json.dumps({
            "title": "Markdown Plan",
            "plan_type": "weekly",
            "items": [
                {"video_id": 1, "day_position": 1, "order_position": 1},
            ],
        })
        response_text = f"```json\n{inner}\n```"
        plan_data, items = parse_response(response_text, valid_video_ids)
        assert plan_data["title"] == "Markdown Plan"
        assert len(items) == 1


class TestCallLLM:
    """Tests for the LLM API call."""

    def test_successful_call(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": '{"title": "Test", "plan_type": "weekly", "items": []}'}}
            ]
        }

        with patch("httpx.post", return_value=mock_response):
            result = call_llm(
                base_url="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
            )
            assert "Test" in result

    def test_timeout_raises_error(self):
        with patch(
            "httpx.post",
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(AIClientError, match="timeout"):
                call_llm(
                    base_url="https://api.example.com/v1",
                    api_key="test-key",
                    model="gpt-4",
                    messages=[],
                )

    def test_auth_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(AIAuthError, match="401"):
                call_llm(
                    base_url="https://api.example.com/v1",
                    api_key="bad-key",
                    model="gpt-4",
                    messages=[],
                )

    def test_server_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(AIServerError, match="500"):
                call_llm(
                    base_url="https://api.example.com/v1",
                    api_key="test-key",
                    model="gpt-4",
                    messages=[],
                )
