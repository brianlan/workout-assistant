"""Tests for the Category API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.models import Category, Video


class TestCreateCategory:
    """POST /api/categories"""

    def test_create_category_valid(self, client: TestClient):
        response = client.post("/api/categories", json={"name": "Strength"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Strength"
        assert data["id"] is not None
        assert data["created_at"] is not None

    def test_create_category_duplicate_name(self, client: TestClient):
        client.post("/api/categories", json={"name": "Cardio"})
        response = client.post("/api/categories", json={"name": "Cardio"})
        assert response.status_code == 409

    def test_create_category_empty_name(self, client: TestClient):
        response = client.post("/api/categories", json={"name": ""})
        assert response.status_code == 422


class TestListCategories:
    """GET /api/categories"""

    def test_list_categories_empty(self, client: TestClient):
        response = client.get("/api/categories")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_categories(self, client: TestClient):
        client.post("/api/categories", json={"name": "Strength"})
        client.post("/api/categories", json={"name": "Cardio"})
        response = client.get("/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [c["name"] for c in data]
        assert "Strength" in names
        assert "Cardio" in names


class TestGetCategory:
    """GET /api/categories/{id}"""

    def test_get_category(self, client: TestClient):
        create_resp = client.post("/api/categories", json={"name": "Yoga"})
        cat_id = create_resp.json()["id"]
        response = client.get(f"/api/categories/{cat_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Yoga"

    def test_get_category_not_found(self, client: TestClient):
        response = client.get("/api/categories/999")
        assert response.status_code == 404


class TestUpdateCategory:
    """PUT /api/categories/{id}"""

    def test_update_category_name(self, client: TestClient):
        create_resp = client.post("/api/categories", json={"name": "Yoga"})
        cat_id = create_resp.json()["id"]
        response = client.put(
            f"/api/categories/{cat_id}", json={"name": "Pilates"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Pilates"

    def test_update_category_duplicate_name(self, client: TestClient):
        client.post("/api/categories", json={"name": "Strength"})
        create_resp = client.post("/api/categories", json={"name": "Yoga"})
        cat_id = create_resp.json()["id"]
        response = client.put(
            f"/api/categories/{cat_id}", json={"name": "Strength"}
        )
        assert response.status_code == 409

    def test_update_category_not_found(self, client: TestClient):
        response = client.put("/api/categories/999", json={"name": "New"})
        assert response.status_code == 404


class TestDeleteCategory:
    """DELETE /api/categories/{id}"""

    def test_delete_category_no_videos(self, client: TestClient):
        create_resp = client.post("/api/categories", json={"name": "Old"})
        cat_id = create_resp.json()["id"]
        response = client.delete(f"/api/categories/{cat_id}")
        assert response.status_code == 204

        # Verify deleted
        get_resp = client.get(f"/api/categories/{cat_id}")
        assert get_resp.status_code == 404

    def test_delete_category_not_found(self, client: TestClient):
        response = client.delete("/api/categories/999")
        assert response.status_code == 404

    def test_delete_category_with_videos_and_reassign(
        self, client: TestClient, engine
    ):
        # Create two categories
        cat1_resp = client.post("/api/categories", json={"name": "Cat1"})
        cat2_resp = client.post("/api/categories", json={"name": "Cat2"})
        cat1_id = cat1_resp.json()["id"]
        cat2_id = cat2_resp.json()["id"]

        # Create a video in cat1 directly in DB
        with Session(engine) as session:
            video = Video(
                title="Test Video",
                category_id=cat1_id,
                file_path="/data/videos/cat1/test.mp4",
                status="ready",
            )
            session.add(video)
            session.commit()
            video_id = video.id

        # Delete cat1 and reassign to cat2
        response = client.delete(
            f"/api/categories/{cat1_id}",
            params={"reassign_to": cat2_id},
        )
        assert response.status_code == 204

        # Verify video reassigned
        with Session(engine) as session:
            from sqlmodel import select

            vid = session.exec(
                select(Video).where(Video.id == video_id)
            ).first()
            assert vid is not None
            assert vid.category_id == cat2_id
