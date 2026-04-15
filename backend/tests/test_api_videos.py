"""Tests for the Video API endpoints — upload portion (Milestone 2)."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Category, Video


def _create_test_mp4(path: Path, duration: int = 3) -> Path:
    """Helper to create a small test MP4 file."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=blue:s=320x240:d={duration}:r=24",
            "-f", "lavfi",
            "-i", f"anoisesrc=d={duration}:r=44100:c=pink:a=0.1",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(path),
        ],
        capture_output=True,
        check=True,
    )
    return path


def _create_test_webm(path: Path, duration: int = 3) -> Path:
    """Helper to create a test WebM file."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=red:s=320x240:d={duration}:r=24",
            "-c:v", "libvpx-vp9", "-crf", "40",
            "-an",
            str(path),
        ],
        capture_output=True,
        check=True,
    )
    return path


def _create_category(client: TestClient, name: str = "Strength") -> int:
    """Helper to create a category via API."""
    resp = client.post("/api/categories", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


class TestVideoUpload:
    """POST /api/videos/upload"""

    def test_upload_mp4(self, client: TestClient, tmp_path):
        """Upload an MP4 file - should be immediately ready."""
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "test.mp4")

        with open(video_path, "rb") as f:
            response = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"category_id": str(cat_id)},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ready"
        assert data["title"] == "test"
        assert data["category_id"] == cat_id
        assert data["id"] is not None

    def test_upload_webm_triggers_transcode(self, client: TestClient, tmp_path):
        """Upload a WebM file - should be transcoding status."""
        cat_id = _create_category(client)
        video_path = _create_test_webm(tmp_path / "test.webm")

        with open(video_path, "rb") as f:
            response = client.post(
                "/api/videos/upload",
                files={"file": ("test.webm", f, "video/webm")},
                data={"category_id": str(cat_id)},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "transcoding"

    def test_upload_with_metadata(self, client: TestClient, tmp_path):
        """Upload with optional metadata fields."""
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "test2.mp4")

        with open(video_path, "rb") as f:
            response = client.post(
                "/api/videos/upload",
                files={"file": ("test2.mp4", f, "video/mp4")},
                data={
                    "category_id": str(cat_id),
                    "title": "My Workout",
                    "description": "A great workout",
                    "difficulty": "intermediate",
                    "muscle_groups": '["chest", "triceps"]',
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Workout"
        assert data["description"] == "A great workout"
        assert data["difficulty"] == "intermediate"
        assert data["muscle_groups"] == '["chest", "triceps"]'

    def test_upload_title_from_filename(self, client: TestClient, tmp_path):
        """Title should be derived from filename if not provided."""
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "my_pushup_workout.mp4")

        with open(video_path, "rb") as f:
            response = client.post(
                "/api/videos/upload",
                files={"file": ("my_pushup_workout.mp4", f, "video/mp4")},
                data={"category_id": str(cat_id)},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "my_pushup_workout"

    def test_upload_invalid_category(self, client: TestClient, tmp_path):
        """Upload with non-existent category should fail."""
        video_path = _create_test_mp4(tmp_path / "test.mp4")

        with open(video_path, "rb") as f:
            response = client.post(
                "/api/videos/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"category_id": "999"},
            )

        assert response.status_code == 400


class TestVideoURLImport:
    """POST /api/videos/import-url"""

    @patch("app.routers.videos.download_video")
    def test_import_valid_url(self, mock_download, client: TestClient, tmp_path):
        """Import from a valid URL should create a video record."""
        import subprocess

        cat_id = _create_category(client)

        # Create a test MP4 for the mock to "download"
        fake_download = tmp_path / "downloaded.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "color=c=blue:s=320x240:d=3:r=24",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-an", str(fake_download),
            ],
            capture_output=True,
            check=True,
        )
        mock_download.return_value = fake_download

        response = client.post(
            "/api/videos/import-url",
            json={
                "url": "https://www.youtube.com/watch?v=test123",
                "category_id": cat_id,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["source_url"] == "https://www.youtube.com/watch?v=test123"
        # After synchronous processing, status should be ready
        assert data["status"] in ("importing", "ready")

    def test_import_duplicate_url(self, client: TestClient, engine):
        """Import a duplicate URL should return 409."""
        from sqlmodel import Session as DBSession
        from app.models import Category, Video

        cat_id = _create_category(client)

        # Create a video with the same source URL
        with DBSession(engine) as session:
            video = Video(
                title="Existing",
                category_id=cat_id,
                file_path="/data/videos/test/existing.mp4",
                source_url="https://youtube.com/watch?v=abc123",
                status="ready",
            )
            session.add(video)
            session.commit()

        response = client.post(
            "/api/videos/import-url",
            json={
                "url": "https://youtube.com/watch?v=abc123",
                "category_id": cat_id,
            },
        )

        assert response.status_code == 409

    def test_import_invalid_url(self, client: TestClient):
        """Import with an invalid URL format should return 422."""
        cat_id = _create_category(client)

        response = client.post(
            "/api/videos/import-url",
            json={
                "url": "",
                "category_id": cat_id,
            },
        )

        assert response.status_code == 422

    def test_import_invalid_category(self, client: TestClient):
        """Import with a non-existent category should return 400."""
        response = client.post(
            "/api/videos/import-url",
            json={
                "url": "https://youtube.com/watch?v=test",
                "category_id": 999,
            },
        )

        assert response.status_code == 400


def _seed_videos(client: TestClient, engine, tmp_path, count=3):
    """Helper to seed test videos via direct DB insert for library tests."""
    from sqlmodel import Session as DBSession

    cat_id = _create_category(client)
    videos = []
    with DBSession(engine) as session:
        for i in range(count):
            v = Video(
                title=f"Video {i+1}",
                description=f"Description {i+1}" if i % 2 == 0 else None,
                category_id=cat_id,
                difficulty=["beginner", "intermediate", "advanced"][i % 3],
                file_path=str(tmp_path / f"video_{i+1}.mp4"),
                status="ready",
            )
            session.add(v)
            videos.append(v)
        session.commit()
        for v in videos:
            session.refresh(v)
    return videos, cat_id


class TestVideoLibrary:
    """GET /api/videos -- list, filter, search."""

    def test_list_videos_paginated(self, client: TestClient, engine, tmp_path):
        _seed_videos(client, engine, tmp_path, count=5)
        response = client.get("/api/videos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 20  # default page size

    def test_list_videos_filter_by_category(self, client: TestClient, engine, tmp_path):
        videos, cat_id = _seed_videos(client, engine, tmp_path, count=3)
        response = client.get("/api/videos", params={"category_id": cat_id})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(v["category_id"] == cat_id for v in data)

    def test_list_videos_search(self, client: TestClient, engine, tmp_path):
        _seed_videos(client, engine, tmp_path, count=3)
        response = client.get("/api/videos", params={"search": "Video 1"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("Video 1" in v["title"] for v in data)

    def test_list_videos_combined_filter(self, client: TestClient, engine, tmp_path):
        videos, cat_id = _seed_videos(client, engine, tmp_path, count=3)
        response = client.get(
            "/api/videos",
            params={"category_id": cat_id, "search": "Video 2"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_videos_empty(self, client: TestClient):
        response = client.get("/api/videos")
        assert response.status_code == 200
        assert response.json() == []


class TestVideoStream:
    """GET /api/videos/{id}/stream"""

    def test_stream_video(self, client: TestClient, tmp_path):
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "streamable.mp4")

        with open(video_path, "rb") as f:
            resp = client.post(
                "/api/videos/upload",
                files={"file": ("streamable.mp4", f, "video/mp4")},
                data={"category_id": str(cat_id)},
            )
        vid_id = resp.json()["id"]

        response = client.get(f"/api/videos/{vid_id}/stream")
        assert response.status_code == 200
        assert "video" in response.headers.get("content-type", "")

    def test_stream_video_range_request(self, client: TestClient, tmp_path):
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "range.mp4")

        with open(video_path, "rb") as f:
            resp = client.post(
                "/api/videos/upload",
                files={"file": ("range.mp4", f, "video/mp4")},
                data={"category_id": str(cat_id)},
            )
        vid_id = resp.json()["id"]

        response = client.get(
            f"/api/videos/{vid_id}/stream",
            headers={"Range": "bytes=0-1023"},
        )
        assert response.status_code == 206


class TestVideoThumbnail:
    """GET /api/videos/{id}/thumbnail"""

    def test_get_thumbnail(self, client: TestClient, tmp_path):
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "thumb_test.mp4")

        with open(video_path, "rb") as f:
            resp = client.post(
                "/api/videos/upload",
                files={"file": ("thumb_test.mp4", f, "video/mp4")},
                data={"category_id": str(cat_id)},
            )
        vid_id = resp.json()["id"]

        response = client.get(f"/api/videos/{vid_id}/thumbnail")
        assert response.status_code == 200
        assert "image" in response.headers.get("content-type", "")


class TestVideoUpdate:
    """PUT /api/videos/{id}"""

    def test_update_video_metadata(self, client: TestClient, tmp_path):
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "update_test.mp4")

        with open(video_path, "rb") as f:
            resp = client.post(
                "/api/videos/upload",
                files={"file": ("update_test.mp4", f, "video/mp4")},
                data={"category_id": str(cat_id)},
            )
        vid_id = resp.json()["id"]

        response = client.put(
            f"/api/videos/{vid_id}",
            json={"title": "Updated Title", "description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "New description"

    def test_update_video_not_found(self, client: TestClient):
        response = client.put("/api/videos/999", json={"title": "Nope"})
        assert response.status_code == 404


class TestVideoDelete:
    """DELETE /api/videos/{id}"""

    def test_delete_video(self, client: TestClient, tmp_path):
        cat_id = _create_category(client)
        video_path = _create_test_mp4(tmp_path / "delete_test.mp4")

        with open(video_path, "rb") as f:
            resp = client.post(
                "/api/videos/upload",
                files={"file": ("delete_test.mp4", f, "video/mp4")},
                data={"category_id": str(cat_id)},
            )
        vid_id = resp.json()["id"]

        response = client.delete(f"/api/videos/{vid_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"/api/videos/{vid_id}/stream")
        assert get_resp.status_code == 404

    def test_delete_video_not_found(self, client: TestClient):
        response = client.delete("/api/videos/999")
        assert response.status_code == 404
