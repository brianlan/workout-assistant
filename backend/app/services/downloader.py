"""Video downloader service: yt-dlp wrapper for downloading videos from URLs."""

import logging
from pathlib import Path
from typing import Callable

import yt_dlp

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when a video download fails."""

    pass


def get_format_options() -> list[str]:
    """Return yt-dlp format selection options.

    Prefers H.264 video + AAC audio, merges to MP4 container.
    """
    return [
        "-S", "vcodec:h264,res,acodec:aac",
        "--merge-output-format", "mp4",
    ]


def download_video(
    url: str,
    output_dir: Path,
    progress_callback: Callable[[dict], None] | None = None,
) -> Path:
    """Download a video from a URL using yt-dlp.

    Args:
        url: The video URL to download.
        output_dir: Directory to save the downloaded video.
        progress_callback: Optional callback for progress updates.

    Returns:
        Path to the downloaded video file.

    Raises:
        DownloadError: If the download fails.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    format_opts = get_format_options()

    ydl_opts: dict = {
        "format_sort": ["vcodec:h264", "res", "acodec:aac"],
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
    }

    if progress_callback:
        ydl_opts["progress_hooks"] = [progress_callback]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the downloaded file
        mp4_files = list(output_dir.glob("*.mp4"))
        if not mp4_files:
            # Check for any video file
            all_files = list(output_dir.iterdir())
            if all_files:
                return all_files[0]
            raise DownloadError("No video file found after download")

        return mp4_files[-1]

    except DownloadError:
        raise
    except Exception as e:
        raise DownloadError(f"Failed to download video: {e}") from e
