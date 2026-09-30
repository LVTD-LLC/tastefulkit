"""Isolated, bounded decoder. Invoked with Python -I, never with Django loaded."""

import io
import json
import sys

import av


def inspect_video(content):
    # Require an MP4 brand, not a renamed MOV/WebM/GIF. Disable all external
    # protocols and MOV external data references; bytes come from memory only.
    if content[4:8] != b"ftyp" or content[8:12] not in {
        b"isom",
        b"iso2",
        b"mp41",
        b"mp42",
        b"avc1",
    }:
        raise ValueError("Not MP4")
    with av.open(
        io.BytesIO(content),
        format="mov",
        options={
            "protocol_whitelist": "",
            "enable_drefs": "0",
            "use_absolute_path": "0",
            "err_detect": "explode",
        },
    ) as container:
        if len(container.streams) != 1 or len(container.streams.video) != 1:
            raise ValueError("One silent video stream required")
        stream = container.streams.video[0]
        codec = stream.codec_context
        if codec.name != "h264" or codec.format.name != "yuv420p":
            raise ValueError("Unsupported codec")
        width, height = codec.width, codec.height
        if not (1 <= width <= 2560 and 1 <= height <= 2560 and width * height <= 4_000_000):
            raise ValueError("Oversize video")
        duration = float((stream.duration or 0) * stream.time_base)
        rate = float(stream.average_rate or 0)
        if not 1 <= duration <= 15 or not 1 <= rate <= 60:
            raise ValueError("Unsupported duration or frame rate")
        codec.thread_count = 1
        codec.options = {"err_detect": "explode"}
        count = 0
        for frame in container.decode(video=0):
            count += 1
            if count > 900 or frame.width != width or frame.height != height:
                raise ValueError("Unexpected frames")
            if frame.time is None or not 0 <= frame.time <= 15:
                raise ValueError("Invalid frame timeline")
        if not count or (stream.frames and count != stream.frames):
            raise ValueError("Incomplete video")
        return {"video_width": width, "video_height": height, "video_duration": duration}


if __name__ == "__main__":
    # Linux production workers: bound native allocation and CPU as well as the
    # parent wall-clock deadline. Other platforms retain the deadline/byte caps.
    if sys.platform == "linux":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    try:
        print(json.dumps(inspect_video(sys.stdin.buffer.read(20 * 1024 * 1024 + 1))))
    except Exception:
        sys.exit(1)
