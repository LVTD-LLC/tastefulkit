import io
from unittest.mock import patch

import av
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.catalogue.models import Design
from apps.catalogue.tests.test_ingestion import bundle, submit

pytestmark = pytest.mark.django_db
NOTES = "On hover, the cards slide upward over approximately 300ms. Reduced motion: no sliding."


@pytest.fixture
def admin_key(user):
    user.is_superuser = True
    user.save()
    return user.profile.rotate_api_key()


def clip_bytes(*, seconds=1, width=64, codec="libx264", format="mp4"):
    out = io.BytesIO()
    with av.open(out, "w", format=format) as container:
        stream = container.add_stream(codec, rate=24)
        stream.width = width
        stream.height = 64
        stream.pix_fmt = "yuv420p"
        for _ in range(seconds * 24):
            frame = av.VideoFrame.from_image(Image.new("RGB", (width, 64), "red"))
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return out.getvalue()


def motion_bundle(**changes):
    files = bundle(motion_notes=NOTES, **changes)
    files["video"] = SimpleUploadedFile("motion.mp4", clip_bytes(), content_type="video/mp4")
    return files


def test_motion_submission_and_public_preview(client, admin_key, qdrant_store):
    files = motion_bundle()
    original = files["video"].read()
    files["video"].seek(0)
    response = submit(client, admin_key, files)
    assert response.status_code == 201, response.content
    design = Design.objects.get()
    data = response.json()
    assert data["video_url"].endswith(".mp4")
    assert data["motion_notes"] == NOTES
    assert data["video_width"] == 64 and data["video_height"] == 64
    assert data["video_duration"] == pytest.approx(1)
    assert design.video.read() == original
    html = client.get(design.get_absolute_url()).content.decode()
    assert "<video" in html and "controls" in html and NOTES in html
    assert "data-motion-detail" in html
    assert "<video" in client.get("/explore/").content.decode()


@pytest.mark.parametrize("content", [b"fake.mp4", b"GIF89a", b"<svg></svg>"])
def test_invalid_video_rejected_without_writes(client, admin_key, content):
    files = motion_bundle()
    files["video"] = SimpleUploadedFile("motion.mp4", content, content_type="video/mp4")
    assert submit(client, admin_key, files).status_code == 422
    assert not Design.objects.exists()


def test_video_needs_motion_notes(client, admin_key):
    files = bundle()
    files["video"] = SimpleUploadedFile("motion.mp4", clip_bytes())
    assert submit(client, admin_key, files).status_code == 422


def test_motion_replacement_and_rollback(
    client, admin_key, qdrant_store, django_capture_on_commit_callbacks
):
    assert submit(client, admin_key, motion_bundle()).status_code == 201
    design = Design.objects.get()
    old_name = design.video.name
    assert submit(client, admin_key).status_code == 200  # idempotent retry preserves clip
    with patch("apps.catalogue.ingestion.upsert_vector", side_effect=TimeoutError):
        assert submit(client, admin_key, motion_bundle(replace_existing=True)).status_code == 503
    design.refresh_from_db()
    assert design.video.name == old_name and design.video.storage.exists(old_name)
    with django_capture_on_commit_callbacks(execute=True):
        assert submit(client, admin_key, bundle(replace_existing=True)).status_code == 200
    design.refresh_from_db()
    assert not design.video and not design.motion_notes and design.video_duration is None
    assert not design.video.storage.exists(old_name)


def test_motion_filter_and_hidden_visibility(client, admin_key, qdrant_store):
    submit(client, admin_key, motion_bundle())
    design = Design.objects.get()
    Design.objects.create(
        fingerprint="static",
        submitted_by=design.submitted_by,
        title="Static",
        capture_status="ready",
    )
    response = client.get("/api/v1/designs?has_motion=true", HTTP_X_API_KEY=admin_key)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    design.published = False
    design.save()
    assert (
        client.get("/api/v1/designs?has_motion=true", HTTP_X_API_KEY=admin_key).json()["total"] == 0
    )
    assert client.get(design.get_absolute_url()).status_code == 404


@pytest.mark.parametrize(
    "kwargs", [{"seconds": 16}, {"width": 2600}, {"codec": "mpeg4"}, {"format": "matroska"}]
)
def test_unsupported_video_properties(kwargs):
    from apps.catalogue.motion import read_video

    with pytest.raises(ValueError):
        read_video(SimpleUploadedFile("motion.mp4", clip_bytes(**kwargs)))


def test_video_size_and_decoder_deadline():
    import subprocess

    from apps.catalogue.motion import MAX_VIDEO_BYTES, read_video

    with pytest.raises(ValueError, match="20 MiB"):
        read_video(io.BytesIO(b"x" * (MAX_VIDEO_BYTES + 1)))
    with patch(
        "apps.catalogue.motion.subprocess.run", side_effect=subprocess.TimeoutExpired("probe", 20)
    ):
        with pytest.raises(ValueError, match="MP4"):
            read_video(io.BytesIO(clip_bytes()))


def test_truncated_video_rejected():
    from apps.catalogue.motion import read_video

    content = clip_bytes()
    with pytest.raises(ValueError):
        read_video(io.BytesIO(content[: len(content) // 2]))


def test_notes_are_escaped_and_no_js_static_fallback(client, admin_key, qdrant_store):
    files = motion_bundle()
    import json

    payload = json.loads(files["payload"])
    payload["motion_notes"] = "<script>alert(1)</script> Scroll reveals cards."
    files["payload"] = json.dumps(payload)
    assert submit(client, admin_key, files).status_code == 201
    design = Design.objects.get()
    html = client.get(design.get_absolute_url()).content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'data-motion-panel="screenshot"' in html and design.screenshot.url in html
    assert client.get("/explore/?has_motion=1").context["page"].paginator.count == 1


@pytest.mark.parametrize("signed_in", [False, True])
def test_motion_filter_is_in_public_search_form(client, user, signed_in):
    import re

    if signed_in:
        client.force_login(user)
    html = client.get("/explore/?has_motion=1").content.decode()
    forms = re.findall(r"<form\b[^>]*>.*?</form>", html, flags=re.S)
    search = next(form for form in forms if 'class="tk-search"' in form)
    assert 'name="has_motion"' in search
    assert re.search(r'<option value="1"\s+selected', search)
    assert html.count('name="has_motion"') == 1
