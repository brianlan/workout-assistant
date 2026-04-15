"""Video processing service: format detection, thumbnail extraction, transcoding."""

import json
import subprocess
from pathlib import Path


def is_web_compatible(file_path: Path) -> bool:
    """Check if a video file is H.264+AAC in MP4 container (browser-playable).

    Returns True only if:
    - Container format is MP4 (mov, mp4, isom, etc.)
    - Video codec is H.264
    - Audio codec is AAC (or no audio)
    """
    file_path = Path(file_path)
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

    probe = json.loads(result.stdout)

    # Check container format
    format_name = probe.get("format", {}).get("format_name", "")
    # MP4 container formats: mov, mp4, isom, ismv, etc.
    mp4_formats = {"mov", "mp4", "isom", "ismv", "m4v"}
    if not any(f in format_name.lower() for f in mp4_formats):
        return False

    streams = probe.get("streams", [])
    video_codec = None
    audio_codec = None

    for stream in streams:
        codec_type = stream.get("codec_type", "")
        codec_name = stream.get("codec_name", "")
        if codec_type == "video":
            video_codec = codec_name
        elif codec_type == "audio":
            audio_codec = codec_name

    # Must have H.264 video
    if video_codec not in ("h264", "avc"):
        return False

    # Audio must be AAC if present
    if audio_codec is not None and audio_codec not in ("aac",):
        return False

    return True


def extract_thumbnail(
    file_path: Path,
    output_path: Path,
    timestamp_ratio: float = 0.25,
) -> Path:
    """Extract a JPEG thumbnail from a video file.

    Attempts to extract at the given ratio of duration (default 25%).
    Falls back to frame 0 if the video is too short.
    """
    file_path = Path(file_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get duration
    duration = _get_duration(file_path)

    if duration and duration > 0:
        seek_time = duration * timestamp_ratio
    else:
        seek_time = 0

    # Extract thumbnail
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(seek_time),
        "-i", str(file_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # If extraction failed at seek time, try from frame 0
    if result.returncode != 0 or not output_path.exists():
        cmd[3] = "0"
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    return output_path


def get_video_metadata(file_path: Path) -> dict:
    """Extract video metadata using ffprobe.

    Returns dict with: duration, format_name, file_size
    """
    file_path = Path(file_path)
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    probe = json.loads(result.stdout)
    fmt = probe.get("format", {})

    return {
        "duration": float(fmt.get("duration", 0)),
        "format_name": fmt.get("format_name", "unknown"),
        "file_size": int(fmt.get("size", 0)),
    }


def transcode_video(input_path: Path, output_path: Path) -> Path:
    """Transcode a video file to H.264+AAC MP4 with faststart.

    Uses preset=veryfast and crf=23 for good balance of speed and quality.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return output_path


def ensure_faststart(input_path: Path) -> Path:
    """Ensure an MP4 file has the faststart flag (moov atom before mdat).

    This rewrites the file in place by copying streams and reordering atoms.
    """
    input_path = Path(input_path)
    temp_path = input_path.with_suffix(".tmp.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(temp_path),
    ]

    subprocess.run(cmd, capture_output=True, text=True, check=True)
    temp_path.replace(input_path)
    return input_path


def _get_duration(file_path: Path) -> float | None:
    """Get video duration in seconds."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        probe = json.loads(result.stdout)
        return float(probe.get("format", {}).get("duration", 0))
    except (subprocess.CalledProcessError, ValueError, KeyError):
        return None
