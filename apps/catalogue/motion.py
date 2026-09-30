"""Validate prepared MP4s without fetching URLs or transforming collector assets."""

import json
import subprocess
import sys
from pathlib import Path

MAX_VIDEO_BYTES = 20 * 1024 * 1024


def read_video(upload):
    content = upload.read(MAX_VIDEO_BYTES + 1)
    if not content or len(content) > MAX_VIDEO_BYTES:
        raise ValueError("Video must be non-empty and at most 20 MiB.")
    # Native decoding runs out-of-process with a deadline. No upload names/URLs
    # enter commands, diagnostics or logs; the worker accepts bytes only.
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).with_name("motion_probe.py"))],
            input=content,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=True,
        )
        metadata = json.loads(result.stdout)
    except (subprocess.SubprocessError, ValueError) as exc:
        raise ValueError(
            "Supply a valid silent H.264/yuv420p MP4: 1–15 seconds, at most "
            "60 fps, 2560px per side and 4 million pixels."
        ) from exc
    return content, metadata
