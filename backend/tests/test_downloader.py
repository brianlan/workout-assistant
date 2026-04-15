"""Tests for the video downloader service."""

from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, select

from app.models import Category, Video
from app.services.downloader import (
    DownloadError,
    get_format_options,
    download_video,
)


class TestFormatOptions:
    """Tests for yt-dlp format selection options."""

    def test_format_selection_prefers_h264_aac(self):
        opts = get_format_options()
        # Should include format sort preference for h264 + aac
        assert "-S" in opts
        idx = opts.index("-S")
        sort_str = opts[idx + 1]
        assert "vcodec:h264" in sort_str
        assert "acodec:aac" in sort_str

    def test_merge_output_format_mp4(self):
        opts = get_format_options()
        assert "--merge-output-format" in opts
        idx = opts.index("--merge-output-format")
        assert opts[idx + 1] == "mp4"


class TestDownloadVideo:
    """Tests for the download_video function."""

    @patch("yt_dlp.YoutubeDL")
    def test_successful_download(self, mock_ytdl_class, tmp_path):
        mock_ytdl = MagicMock()
        mock_ytdl.download.return_value = None  # success
        mock_ytdl_class.return_value.__enter__ = MagicMock(return_value=mock_ytdl)
        mock_ytdl_class.return_value.__exit__ = MagicMock(return_value=False)

        output_dir = tmp_path / "downloads"
        output_dir.mkdir()

        # Create a dummy file to simulate download output
        (output_dir / "test_video.mp4").write_bytes(b"fake video")

        # Should not raise
        download_video("https://www.youtube.com/watch?v=test123", output_dir)

        mock_ytdl.download.assert_called_once()

    @patch("yt_dlp.YoutubeDL")
    def test_invalid_url_raises_error(self, mock_ytdl_class, tmp_path):
        mock_ytdl = MagicMock()
        mock_ytdl.download.side_effect = Exception("Video not found")
        mock_ytdl_class.return_value.__enter__ = MagicMock(return_value=mock_ytdl)
        mock_ytdl_class.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(DownloadError, match="Video not found"):
            download_video("https://invalid-url.example.com/video", tmp_path)

    @patch("yt_dlp.YoutubeDL")
    def test_progress_hook_called(self, mock_ytdl_class, tmp_path):
        progress_callback = MagicMock()
        mock_ytdl = MagicMock()
        mock_ytdl.download.return_value = None
        mock_ytdl_class.return_value.__enter__ = MagicMock(return_value=mock_ytdl)
        mock_ytdl_class.return_value.__exit__ = MagicMock(return_value=False)

        # Create a dummy file to simulate download output
        (tmp_path / "test_video.mp4").write_bytes(b"fake video")

        download_video(
            "https://www.youtube.com/watch?v=test123",
            tmp_path,
            progress_callback=progress_callback,
        )

        # Verify YoutubeDL was called with progress_hooks
        call_args = mock_ytdl_class.call_args
        opts = call_args[0][0] if call_args[0] else call_args.kwargs
        assert "progress_hooks" in opts
        assert progress_callback in opts["progress_hooks"]


class TestDuplicateDetection:
    """Tests for duplicate URL detection."""

    def test_duplicate_source_url_detected(self, session: Session):
        # Create a category first
        cat = Category(name="Test")
        session.add(cat)
        session.commit()

        video1 = Video(
            title="Existing Video",
            category_id=cat.id,
            file_path="/data/videos/test/existing.mp4",
            source_url="https://youtube.com/watch?v=abc123",
            status="ready",
        )
        session.add(video1)
        session.commit()

        result = session.exec(
            select(Video).where(Video.source_url == "https://youtube.com/watch?v=abc123")
        ).first()
        assert result is not None
        assert result.source_url == "https://youtube.com/watch?v=abc123"

    def test_no_duplicate_for_different_urls(self, session: Session):
        cat = Category(name="Test2")
        session.add(cat)
        session.commit()

        video1 = Video(
            title="Video 1",
            category_id=cat.id,
            file_path="/data/videos/test/v1.mp4",
            source_url="https://youtube.com/watch?v=abc123",
            status="ready",
        )
        session.add(video1)
        session.commit()

        result = session.exec(
            select(Video).where(Video.source_url == "https://youtube.com/watch?v=xyz789")
        ).first()
        assert result is None
