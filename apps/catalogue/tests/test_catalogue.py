from unittest.mock import patch

import pytest
from django.contrib.auth.models import User

from apps.catalogue.models import Design, SavedDesign
from apps.catalogue.providers import EMBEDDING_MODEL, public_url
from apps.catalogue.services import search_designs

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


def test_search_fallback_filters_and_hidden_designs(design):
    with patch("apps.catalogue.services.embed", side_effect=ValueError("offline")):
        matches, mode = search_designs("warm")
        assert list(matches) == [design]
        assert mode == "text"
        assert list(search_designs("warm", kind="hero")[0]) == []
        design.published = False
        design.save()
        assert list(search_designs("warm")[0]) == []


def test_semantic_results_include_related_designs(design, qdrant_store):
    from apps.catalogue.vector_store import upsert_vector

    vector = [1.0] + [0.0] * 767
    upsert_vector(design.pk, vector)
    design.embedding_model = EMBEDDING_MODEL
    design.save()
    with patch("apps.catalogue.services.embed", return_value=vector):
        matches, mode = search_designs("cozy")
    assert matches == [design] and mode == "semantic"


def test_library_save_and_visibility(client, user, design, paid_user):
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
