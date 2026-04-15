"""Tests for video processing service."""

import subprocess
from pathlib import Path

import pytest

from app.services.video_processor import (
    extract_thumbnail,
    get_video_metadata,
    is_web_compatible,
    transcode_video,
)


@pytest.fixture(name="mp4_h264_aac", autouse=True)
def mp4_h264_aac_fixture(tmp_path):
    """Create a small H.264+AAC MP4 test video."""
    video_path = tmp_path / "test_h264.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=blue:s=320x240:d=5:r=24",
            "-f", "lavfi",
            "-i", "anoisesrc=d=5:r=44100:c=pink:a=0.1",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    return video_path


@pytest.fixture(name="webm_vp9")
def webm_vp9_fixture(tmp_path):
    """Create a VP9+Opus WebM test video."""
    video_path = tmp_path / "test_vp9.webm"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=red:s=320x240:d=3:r=24",
            "-c:v", "libvpx-vp9", "-crf", "40",
            "-an",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    return video_path


@pytest.fixture(name="mkv_h265")
def mkv_h265_fixture(tmp_path):
    """Create an HEVC MKV test video."""
    video_path = tmp_path / "test_h265.mkv"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=green:s=320x240:d=3:r=24",
            "-c:v", "libx265", "-preset", "ultrafast",
            "-an",
            str(video_path),
        ],
        capture_output=True,
        check=True,
    )
    return video_path


class TestIsWebCompatible:
    """Tests for video format detection."""

    def test_h264_aac_mp4_is_compatible(self, mp4_h264_aac):
        assert is_web_compatible(mp4_h264_aac) is True

    def test_vp9_webm_not_compatible(self, webm_vp9):
        assert is_web_compatible(webm_vp9) is False

    def test_hevc_mkv_not_compatible(self, mkv_h265):
        assert is_web_compatible(mkv_h265) is False

    def test_non_mp4_container_not_compatible(self, webm_vp9):
        assert is_web_compatible(webm_vp9) is False


class TestExtractThumbnail:
    """Tests for thumbnail extraction."""

    def test_extract_thumbnail_from_video(self, mp4_h264_aac, tmp_path):
        output_path = tmp_path / "thumb.jpg"
        extract_thumbnail(mp4_h264_aac, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        # Verify it's a valid JPEG
        header = output_path.read_bytes()[:3]
        assert header[:2] == b"\xff\xd8"

    def test_extract_thumbnail_short_video(self, tmp_path):
        """Very short video (< 5 seconds) should still produce thumbnail."""
        video_path = tmp_path / "short.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "color=c=white:s=320x240:d=1:r=24",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-an", str(video_path),
            ],
            capture_output=True,
            check=True,
        )
        output_path = tmp_path / "thumb_short.jpg"
        extract_thumbnail(video_path, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0


class TestGetVideoMetadata:
    """Tests for metadata extraction."""

    def test_metadata_duration(self, mp4_h264_aac):
        meta = get_video_metadata(mp4_h264_aac)
        assert "duration" in meta
        assert meta["duration"] > 0

    def test_metadata_format(self, mp4_h264_aac):
        meta = get_video_metadata(mp4_h264_aac)
        assert "format_name" in meta
        assert "mp4" in meta["format_name"].lower() or "mov" in meta["format_name"].lower()

    def test_metadata_file_size(self, mp4_h264_aac):
        meta = get_video_metadata(mp4_h264_aac)
        assert "file_size" in meta
        assert meta["file_size"] > 0


class TestTranscodeVideo:
    """Tests for video transcoding."""

    def test_transcode_webm_to_mp4(self, webm_vp9, tmp_path):
        output_path = tmp_path / "transcoded.mp4"
        transcode_video(webm_vp9, output_path)
        assert output_path.exists()
        # Verify the output is H.264+AAC MP4
        assert is_web_compatible(output_path) is True
