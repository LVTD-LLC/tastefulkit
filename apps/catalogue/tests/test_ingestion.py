import io
import json
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django_q.models import Schedule
from PIL import Image

from apps.catalogue.models import Design
from apps.catalogue.providers import EMBEDDING_MODEL
from apps.catalogue.tasks import index_design, process_design

pytestmark = pytest.mark.django_db
VECTOR = [1.0] + [0.0] * 767
GUIDE = """---
version: alpha
name: Warm editorial
colors:
  primary: "#222222"
  neutral: "#ffffff"
typography:
  body:
    fontFamily: Georgia
    fontSize: 16px
components:
  card:
    textColor: "{colors.primary}"
---
## Overview
Warm editorial reference with generous whitespace. Preserve the serif headings and quiet palette.
## Layout
Use a single readable column on mobile. Spacing values are inferred from the supplied screenshot.
"""


def image_file(width=320, height=240):
    content = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(content, "PNG")
    return SimpleUploadedFile("reference.png", content.getvalue(), content_type="image/png")


@pytest.fixture
def admin_key(user):
    user.is_superuser = True
    user.is_staff = True
    user.save()
    return user.profile.rotate_api_key()


def bundle(**changes):
    payload = {
        "title": "Warm editorial reference",
        "source_url": "https://example.com/",
        "description": "A warm editorial design with serif typography and whitespace.",
        "tags": ["Warm", "minimal"],
        "viewport_width": 320,
        "captured_at": "2026-09-16T12:00:00Z",
        "embedding_model": EMBEDDING_MODEL,
        "embedding": VECTOR,
    }
    payload.update(changes)
    return {
        "payload": json.dumps(payload),
        "screenshot": image_file(),
        "thumbnail": image_file(),
        "design_md": SimpleUploadedFile("DESIGN.md", GUIDE.encode(), content_type="text/markdown"),
    }


def submit(client, key, files=None):
    with patch("apps.catalogue.ingestion.public_url", return_value="https://example.com/"):
        return client.post("/api/v1/designs", files or bundle(), HTTP_AUTHORIZATION=f"Bearer {key}")


def test_complete_admin_submission_is_ready_and_preserves_bytes(
    client, user, admin_key, qdrant_store
):
    files = bundle()
    shot = files["screenshot"].read()
    files["screenshot"].seek(0)
    with patch("apps.catalogue.providers.cloudflare_request") as provider:
        first = submit(client, admin_key, files)
        assert first.status_code == 201, first.content
        again = submit(client, admin_key)
        assert again.status_code == 200
        provider.assert_not_called()
    assert first.json()["id"] == again.json()["id"]
    design = Design.objects.get()
    assert design.capture_status == "ready" and design.published
    assert design.design_markdown == GUIDE
    assert design.screenshot.read() == shot
    assert design.embedding == []
    assert (
        qdrant_store.retrieve("test-designs", ids=[str(design.pk)], with_vectors=True)[0].vector
        == VECTOR
    )
    assert not Schedule.objects.exists()
    assert set(design.tags.values_list("name", flat=True)) == {"warm", "minimal"}
    assert (
        client.get(f"/api/v1/designs/{design.pk}", HTTP_X_API_KEY=admin_key).json()[
            "design_markdown"
        ]
        == GUIDE
    )
    assert (
        "design_markdown"
        not in client.get("/api/v1/designs", HTTP_X_API_KEY=admin_key).json()["items"][0]
    )


def test_submission_auth_boundaries(client, user, qdrant_store):
    key = user.profile.rotate_api_key()
    assert submit(client, "invalid").status_code == 401
    assert submit(client, key).status_code == 401
    user.is_staff = True
    user.save()
    assert submit(client, key).status_code == 401
    user.is_superuser = True
    user.is_active = False
    user.save()
    assert submit(client, key).status_code == 401
    assert not Design.objects.exists()


@pytest.mark.parametrize("field", ["screenshot", "thumbnail", "design_md"])
def test_missing_artifacts_rejected_before_creation(client, admin_key, field):
    files = bundle()
    files.pop(field)
    assert submit(client, admin_key, files).status_code == 422
    assert not Design.objects.exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"embedding": [0.0] * 768},
        {"embedding": [1.0] * 3},
        {"embedding": [float("nan")] * 768},
        {"embedding_model": "wrong-model"},
        {"captured_at": "2026-09-16T12:00:00"},
        {"published": True},
    ],
)
def test_invalid_payload_rejected(client, admin_key, changes):
    assert submit(client, admin_key, bundle(**changes)).status_code == 422
    assert not Design.objects.exists()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "# No tokens",
        GUIDE.replace("colors.primary", "colors.missing"),
        GUIDE.replace("name: Warm editorial", "name: Warm\nname: Duplicate"),
        GUIDE.replace('primary: "#222222"', 'primary: "{colors.primary}"'),
        GUIDE.replace("name: Warm editorial", "name: &name Warm\ndescription: *name"),
        GUIDE.replace(
            "fontSize: 16px", "fontSize: 16px\n    invalid: !!python/object/apply:os.system []"
        ),
    ],
)
def test_invalid_markdown_rejected(client, admin_key, text):
    files = bundle()
    files["design_md"] = SimpleUploadedFile("DESIGN.md", text.encode())
    assert submit(client, admin_key, files).status_code == 422
    assert not Design.objects.exists()


@pytest.mark.parametrize("field", ["screenshot", "thumbnail"])
def test_fake_images_are_not_accepted(client, admin_key, field):
    files = bundle()
    files[field] = SimpleUploadedFile(
        "photo.png", b"<svg onload='alert(1)'></svg>", content_type="image/png"
    )
    assert submit(client, admin_key, files).status_code == 422
    assert not Design.objects.exists()


def test_index_failure_rolls_back_database_and_files(
    client, admin_key, qdrant_store, tmp_path, settings
):
    settings.MEDIA_ROOT = tmp_path
    with patch("apps.catalogue.ingestion.upsert_vector", side_effect=TimeoutError):
        result = submit(client, admin_key)
    assert result.status_code == 503
    assert not Design.objects.exists()
    assert not list(tmp_path.rglob("*.png"))
    assert not Schedule.objects.exists()


def test_replace_is_explicit_and_preserves_identity_and_visibility(client, admin_key, qdrant_store):
    first = submit(client, admin_key)
    design = Design.objects.get()
    original_shot = design.screenshot.name
    design.published = False
    design.save()
    assert (
        submit(client, admin_key, bundle(title="Replacement title")).json()["title"] == design.title
    )
    updated = submit(client, admin_key, bundle(title="Replacement title", replace_existing=True))
    assert updated.status_code == 200 and updated.json()["id"] == first.json()["id"]
    design.refresh_from_db()
    assert design.title == "Replacement title" and not design.published
    assert design.screenshot.name != original_shot
    assert Design.objects.count() == 1


def test_failed_replacement_restores_old_content_and_vector(client, admin_key, qdrant_store):
    submit(client, admin_key)
    design = Design.objects.get()
    from apps.catalogue.vector_store import upsert_vector

    def write_then_timeout(pk, vector):
        upsert_vector(pk, vector)
        raise TimeoutError

    with patch("apps.catalogue.ingestion.upsert_vector", side_effect=write_then_timeout):
        result = submit(
            client,
            admin_key,
            bundle(
                title="Replacement title", replace_existing=True, embedding=[0.0, 1.0] + [0.0] * 766
            ),
        )
    assert result.status_code == 503
    previous_title = design.title
    previous_shot = design.screenshot.name
    design.refresh_from_db()
    assert design.title == previous_title and design.screenshot.name == previous_shot
    assert (
        qdrant_store.retrieve("test-designs", ids=[str(design.pk)], with_vectors=True)[0].vector
        == VECTOR
    )


def test_markdown_download_and_html_are_safe_and_scoped(client, user, admin_key, qdrant_store):
    files = bundle()
    malicious = GUIDE + '\n<script>alert("unsafe")</script>\n'
    files["design_md"] = SimpleUploadedFile("DESIGN.md", malicious.encode())
    submit(client, admin_key, files)
    design = Design.objects.get()
    url = f"/designs/{design.pk}/DESIGN.md"
    assert client.get(url).status_code == 302
    client.force_login(user)
    response = client.get(url)
    assert response.content.decode() == malicious
    assert response["Content-Disposition"] == 'attachment; filename="DESIGN.md"'
    html = client.get(design.get_absolute_url()).content.decode()
    assert '<script>alert("unsafe")</script>' not in html
    assert "&lt;script&gt;" in html
    design.published = False
    design.save()
    assert client.get(url).status_code == 404


def test_retired_entrypoints_never_generate(client, admin_key, user):
    design = Design.objects.create(
        submitted_by=user, fingerprint="retired", capture_status="pending"
    )
    with patch("apps.catalogue.providers.cloudflare_request") as provider:
        process_design(design.pk)
        index_design(design.pk)
        assert (
            client.post(f"/api/v1/designs/{design.pk}/retry", HTTP_X_API_KEY=admin_key).status_code
            == 404
        )
        provider.assert_not_called()
    assert not Schedule.objects.exists()
    design.refresh_from_db()
    assert design.capture_status == "pending"


def test_backfill_cannot_generate_missing_vectors(user, qdrant_store):
    Design.objects.create(submitted_by=user, fingerprint="legacy", capture_status="ready")
    with patch("apps.catalogue.providers.cloudflare_request") as provider:
        with pytest.raises(CommandError, match="prepared"):
            call_command("backfill_qdrant")
        provider.assert_not_called()


@pytest.mark.django_db(transaction=True)
def test_commit_failure_removes_new_vector(client, admin_key, qdrant_store):
    from django.db import DatabaseError, connection

    with patch.object(connection, "commit", side_effect=DatabaseError):
        response = submit(client, admin_key)
    assert response.status_code == 503
    assert not Design.objects.exists()
    assert qdrant_store.get_collection("test-designs").points_count == 0
