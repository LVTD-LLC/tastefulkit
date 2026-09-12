import io
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from PIL import Image

from apps.catalogue.models import Design, SavedDesign
from apps.catalogue.providers import EMBEDDING_MODEL, public_url
from apps.catalogue.services import search_designs
from apps.catalogue.tasks import process_design

pytestmark = pytest.mark.django_db


@pytest.fixture
def design(user):
    return Design.objects.create(
        title="Warm minimal website",
        source_url="https://example.com/",
        fingerprint="a" * 64,
        description="Warm typography and generous whitespace.",
        submitted_by=user,
        capture_status="ready",
        screenshot="shot.jpg",
        thumbnail="thumb.jpg",
    )


def test_first_signup_is_not_admin(user):
    user.refresh_from_db()
    assert not user.is_superuser and not user.is_staff


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://[::1]/",
        "file:///etc/passwd",
        "https://user:password@example.com/",
        "https://example.com:8080/",
    ],
)
def test_private_or_unsafe_sources_rejected(url):
    with pytest.raises(ValueError):
        public_url(url)


def test_submission_requires_admin_and_is_idempotent(
    client, user, django_capture_on_commit_callbacks
):
    key = user.profile.rotate_api_key()
    payload = {
        "title": "Example site",
        "source_url": "https://example.com/",
        "description": "A warm, minimal landing page.",
        "tags": ["Warm", "minimal"],
    }
    assert (
        client.post("/api/v1/designs", payload, content_type="application/json").status_code == 401
    )
    assert (
        client.post(
            "/api/v1/designs", payload, content_type="application/json", HTTP_X_API_KEY=key
        ).status_code
        == 401
    )
    user.is_superuser = True
    user.save()
    with (
        patch("apps.catalogue.services.public_url", return_value="https://example.com/"),
        patch("apps.catalogue.services.async_task") as enqueue,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            first = client.post(
                "/api/v1/designs", payload, content_type="application/json", HTTP_X_API_KEY=key
            )
        assert first.status_code == 201, first.content
        second = client.post(
            "/api/v1/designs", payload, content_type="application/json", HTTP_X_API_KEY=key
        )
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
        assert enqueue.call_count == 1
    assert Design.objects.count() == 1
    assert set(Design.objects.get().tags.values_list("name", flat=True)) == {"warm", "minimal"}
    user.is_active = False
    user.save()
    assert client.get("/api/v1/designs", HTTP_X_API_KEY=key).status_code == 401


def test_capture_creates_images_and_embedding(design):
    design.capture_status = "pending"
    design.save()
    image = io.BytesIO()
    Image.new("RGB", (1440, 1800), "white").save(image, "JPEG")
    with (
        patch("apps.catalogue.tasks.capture", return_value=image.getvalue()),
        patch("apps.catalogue.tasks.embed", return_value=[0.1] * 768),
    ):
        process_design(design.pk)
    design.refresh_from_db()
    assert design.capture_status == "ready"
    assert design.screenshot.storage.exists(design.screenshot.name)
    assert design.thumbnail.storage.exists(design.thumbnail.name)
    assert len(design.embedding) == 768
    assert design.embedding_model == EMBEDDING_MODEL


def test_capture_failure_not_published(design):
    design.capture_status = "pending"
    design.save()
    with patch("apps.catalogue.tasks.capture", side_effect=ValueError("Provider unavailable")):
        process_design(design.pk)
    design.refresh_from_db()
    assert design.capture_status == "failed"
    assert list(search_designs()[0]) == []


def test_search_fallback_filters_and_hidden_designs(design):
    with patch("apps.catalogue.services.embed", side_effect=ValueError("offline")):
        matches, mode = search_designs("warm")
        assert list(matches) == [design]
        assert mode == "text"
        assert list(search_designs("warm", kind="hero")[0]) == []
        design.published = False
        design.save()
        assert list(search_designs("warm")[0]) == []


def test_semantic_results_include_related_designs(design):
    design.embedding = [1.0, 0.0]
    design.embedding_model = EMBEDDING_MODEL
    design.save()
    with patch("apps.catalogue.services.embed", return_value=[1.0, 0.0]):
        matches, mode = search_designs("cozy")
    assert matches == [design] and mode == "semantic"


def test_library_save_and_visibility(client, user, design):
    assert client.get("/explore/").status_code == 302
    client.force_login(user)
    assert client.get("/explore/").status_code == 200
    assert client.get(design.get_absolute_url()).status_code == 200
    assert client.get(f"/designs/{design.pk}/save/").status_code == 405
    assert client.post(f"/designs/{design.pk}/save/").status_code == 302
    other = User.objects.create_user(username="other", email="other@example.com")
    SavedDesign.objects.create(user=other, design=design)
    client.post(f"/designs/{design.pk}/save/", {"action": "remove"})
    assert not SavedDesign.objects.filter(user=user).exists()
    assert SavedDesign.objects.filter(user=other).exists()
    design.published = False
    design.save()
    assert client.get(design.get_absolute_url()).status_code == 404


def test_control_characters_in_search_do_not_break_postgres(design):
    with patch("apps.catalogue.services.embed", side_effect=ValueError("offline")):
        matches, mode = search_designs("warm\x00", tag="\x00")
    assert list(matches) == [design]
    assert mode == "text"


def test_rate_limited_capture_is_scheduled_then_bounded(design):
    from django_q.models import Schedule

    from apps.catalogue.providers import RetryableProviderError

    design.capture_status = "pending"
    design.save()
    with patch("apps.catalogue.tasks.capture", side_effect=RetryableProviderError(60)):
        process_design(design.pk)
        design.refresh_from_db()
        assert design.capture_status == "pending"
        scheduled = Schedule.objects.get(name=f"capture-retry-{design.pk}")
        assert scheduled.kwargs == "attempt=1"
        process_design(design.pk, attempt=3)
    design.refresh_from_db()
    assert design.capture_status == "failed"
    assert "exhausted" in design.capture_error
