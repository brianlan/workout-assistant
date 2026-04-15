"""Video API router — upload, library, stream, edit, delete."""

import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.models import Category, Video
from app.services.video_processor import (
    ensure_faststart,
    extract_thumbnail,
    get_video_metadata,
    is_web_compatible,
    transcode_video,
)
from app.services.downloader import download_video

router = APIRouter(prefix="/api/videos", tags=["videos"])


class VideoRead(BaseModel):
    id: int
    title: str
    description: str | None = None
    category_id: int
    difficulty: str | None = None
    muscle_groups: str | None = None
    duration: float | None = None
    format: str | None = None
    file_size: int | None = None
    thumbnail_path: str | None = None
    file_path: str
    source_url: str | None = None
    status: str
    imported_at: datetime

    model_config = {"from_attributes": True}


@router.post("/upload", response_model=VideoRead, status_code=201)
def upload_video(
    file: UploadFile,
    category_id: int = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    difficulty: str | None = Form(None),
    muscle_groups: str | None = Form(None),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Upload a video file.

    - MP4/H.264+AAC files are immediately ready.
    - Other formats are queued for background transcoding.
    """

    # Validate category
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")

    # Save uploaded file to temp location
    temp_dir = settings.data_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}_{file.filename}"

    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Determine video metadata
        metadata = get_video_metadata(temp_path)
        compatible = is_web_compatible(temp_path)

        # Prepare storage directory
        category_dir = settings.videos_dir / _safe_dir_name(category.name)
        category_dir.mkdir(parents=True, exist_ok=True)
        thumbnails_dir = settings.thumbnails_dir
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

        video_uuid = uuid.uuid4().hex
        final_path = category_dir / f"{video_uuid}.mp4"
        thumb_path = thumbnails_dir / f"{video_uuid}.jpg"

        # Derive title from filename if not provided
        video_title = title
        if not video_title:
            stem = Path(file.filename or "untitled").stem
            video_title = stem

        if compatible:
            # Move file to final location and ensure faststart
            shutil.move(str(temp_path), str(final_path))
            ensure_faststart(final_path)
            status = "ready"
        else:
            # Move original file; return transcoding status
            # Background transcoding will convert to MP4 later
            orig_ext = Path(file.filename or "video.mkv").suffix
            temp_final = category_dir / f"{video_uuid}{orig_ext}"
            shutil.move(str(temp_path), str(temp_final))
            final_path = temp_final
            status = "transcoding"

        # Extract thumbnail
        try:
            extract_thumbnail(final_path, thumb_path)
        except Exception:
            thumb_path = None

        # Create DB record
        video = Video(
            title=video_title,
            description=description,
            category_id=category_id,
            difficulty=difficulty,
            muscle_groups=muscle_groups,
            duration=metadata.get("duration"),
            format=metadata.get("format_name"),
            file_size=final_path.stat().st_size,
            thumbnail_path=str(thumb_path) if thumb_path else None,
            file_path=str(final_path),
            source_url=None,
            status=status,
        )
        session.add(video)
        session.commit()
        session.refresh(video)

        return video

    except Exception:
        # Clean up temp file on error
        temp_path.unlink(missing_ok=True)
        raise


def _safe_dir_name(name: str) -> str:
    """Create a filesystem-safe directory name from a category name."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name.lower())


class URLImportRequest(BaseModel):
    url: str
    category_id: int
    title: str | None = None
    description: str | None = None
    difficulty: str | None = None
    muscle_groups: str | None = None

    @field_validator("url")
    @classmethod
    def url_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("url must not be empty")
        return v.strip()


@router.post("/import-url", response_model=VideoRead, status_code=202)
def import_url(
    data: URLImportRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Import a video from a URL.

    Creates a video record with status=importing.
    The actual download is processed synchronously for simplicity.
    """
    # Validate category
    category = session.get(Category, data.category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")

    # Check for duplicate source URL
    existing = session.exec(
        select(Video).where(Video.source_url == data.url)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Video with this URL already exists: {existing.title}",
        )

    # Create DB record with importing status
    video_uuid = uuid.uuid4().hex
    category_dir = settings.videos_dir / _safe_dir_name(category.name)
    category_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = settings.data_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    video_title = data.title or "Importing..."
    video = Video(
        title=video_title,
        description=data.description,
        category_id=data.category_id,
        difficulty=data.difficulty,
        muscle_groups=data.muscle_groups,
        file_path=str(category_dir / f"{video_uuid}.mp4"),
        source_url=data.url,
        status="importing",
    )
    session.add(video)
    session.commit()
    session.refresh(video)

    # Synchronous download (for simplicity)
    try:
        downloaded_path = download_video(data.url, temp_dir)

        # Process the downloaded file
        metadata = get_video_metadata(downloaded_path)
        compatible = is_web_compatible(downloaded_path)

        final_path = category_dir / f"{video_uuid}.mp4"

        if compatible:
            shutil.move(str(downloaded_path), str(final_path))
            ensure_faststart(final_path)
            video.status = "ready"
        else:
            transcode_video(downloaded_path, final_path)
            downloaded_path.unlink(missing_ok=True)
            video.status = "ready"

        # Extract thumbnail
        thumbnails_dir = settings.thumbnails_dir
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumbnails_dir / f"{video_uuid}.jpg"
        try:
            extract_thumbnail(final_path, thumb_path)
            video.thumbnail_path = str(thumb_path)
        except Exception:
            pass

        video.title = data.title or video_title
        video.file_path = str(final_path)
        video.duration = metadata.get("duration")
        video.format = metadata.get("format_name")
        video.file_size = final_path.stat().st_size

        session.add(video)
        session.commit()
        session.refresh(video)

    except Exception:
        video.status = "failed"
        session.add(video)
        session.commit()
        session.refresh(video)

    return video


class VideoUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    difficulty: str | None = None
    muscle_groups: str | None = None


@router.get("", response_model=list[VideoRead])
def list_videos(
    category_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
):
    """List videos with optional filtering and pagination."""
    query = select(Video)

    if category_id is not None:
        query = query.where(Video.category_id == category_id)

    if search:
        query = query.where(
            (Video.title.contains(search))
            | (Video.description.contains(search))
        )

    query = query.offset((page - 1) * page_size).limit(page_size)
    videos = session.exec(query).all()
    return videos


@router.get("/{video_id}/stream")
def stream_video(
    video_id: int,
    session: Session = Depends(get_session),
):
    """Stream a video file. Supports range requests for seeking."""
    from fastapi.responses import FileResponse

    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = Path(video.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        str(file_path),
        media_type="video/mp4",
        filename=file_path.name,
    )


@router.get("/{video_id}/thumbnail")
def get_thumbnail(
    video_id: int,
    session: Session = Depends(get_session),
):
    """Get the thumbnail image for a video."""
    from fastapi.responses import FileResponse

    video = session.get(Video, video_id)
    if not video or not video.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    thumb_path = Path(video.thumbnail_path)
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")

    return FileResponse(
        str(thumb_path),
        media_type="image/jpeg",
    )


@router.put("/{video_id}", response_model=VideoRead)
def update_video(
    video_id: int,
    data: VideoUpdateRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Update video metadata."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if data.title is not None:
        video.title = data.title
    if data.description is not None:
        video.description = data.description
    if data.difficulty is not None:
        video.difficulty = data.difficulty
    if data.muscle_groups is not None:
        video.muscle_groups = data.muscle_groups

    if data.category_id is not None and data.category_id != video.category_id:
        # Validate new category
        new_cat = session.get(Category, data.category_id)
        if not new_cat:
            raise HTTPException(status_code=400, detail="Category not found")

        # Move file to new category directory
        old_path = Path(video.file_path)
        if old_path.exists():
            new_cat_dir = settings.videos_dir / _safe_dir_name(new_cat.name)
            new_cat_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_cat_dir / old_path.name
            shutil.move(str(old_path), str(new_path))
            video.file_path = str(new_path)

        video.category_id = data.category_id

    session.add(video)
    session.commit()
    session.refresh(video)
    return video


@router.delete("/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    session: Session = Depends(get_session),
):
    """Delete a video and its associated files."""
    video = session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Remove video file
    file_path = Path(video.file_path)
    if file_path.exists():
        file_path.unlink()

    # Remove thumbnail
    if video.thumbnail_path:
        thumb_path = Path(video.thumbnail_path)
        if thumb_path.exists():
            thumb_path.unlink()

    # Update any plan items referencing this video
    from app.models import PlanItem

    plan_items = session.exec(
        select(PlanItem).where(PlanItem.video_id == video_id)
    ).all()
    for item in plan_items:
        item.video_id = None
        session.add(item)

    # Remove DB record
    session.delete(video)
    session.commit()
    return None
