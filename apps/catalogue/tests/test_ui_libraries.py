import json
from unittest.mock import patch

import pytest

from apps.catalogue.models import Design
from apps.catalogue.tests.test_ingestion import bundle

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_key(user):
    user.is_superuser = True
    user.is_staff = True
    user.save()
    return user.profile.rotate_api_key()


def submission(client, key, **changes):
    metadata = changes.pop(
        "library",
        {
            "github_url": "https://github.com/example/ui",
            "frameworks": ["React"],
            "notes": "Useful for accessible product interfaces.",
            "pricing_checked_at": "2026-09-29",
            "pricing": [
                {"name": "Personal", "billing": "one_time", "amount": "49.00", "currency": "USD"}
            ],
        },
    )
    files = bundle(kind="ui_library", library=metadata, **changes)
    if "name" in changes:
        payload = json.loads(files["payload"])
        payload.pop("title")
        files["payload"] = json.dumps(payload)
    with patch("apps.catalogue.ingestion.public_url", side_effect=lambda url: url):
        return client.post("/api/v1/ui-libraries", files, HTTP_X_API_KEY=key)


def test_library_submission_public_pages_and_api(client, admin_key, qdrant_store):
    response = submission(client, admin_key)
    assert response.status_code == 201, response.content
    item = response.json()
    assert item["library"]["frameworks"] == ["React"]
    design = Design.objects.get()
    assert design.get_absolute_url() == f"/ui-libraries/{design.pk}/"
    for url in ["/ui-libraries/", design.get_absolute_url()]:
        page = client.get(url)
        assert page.status_code == 200
        assert b"Warm editorial reference" in page.content
    detail = client.get(design.get_absolute_url()).content.decode()
    assert "49.00" in detail and "one-time" in detail and "React" in detail
    assert "noindex" not in detail
    assert design.get_absolute_url() in client.get("/sitemap.xml").content.decode()
    assert client.get("/api/v1/ui-libraries").status_code == 401
    assert client.get("/api/v1/ui-libraries", HTTP_X_API_KEY=admin_key).json()["total"] == 1
    assert (
        client.get(f"/api/v1/ui-libraries/{design.pk}", HTTP_X_API_KEY=admin_key).json()["library"]
        == item["library"]
    )
    assert "post" not in client.get("/api/openapi.json").json()["paths"]["/api/v1/ui-libraries"]
    design.published = False
    design.save()
    assert client.get(design.get_absolute_url()).status_code == 404
    assert design.get_absolute_url() not in client.get("/sitemap.xml").content.decode()


def test_submission_auth_idempotency_and_atomic_replace(client, user, admin_key, qdrant_store):
    assert submission(client, "").status_code == 401
    assert submission(client, admin_key).status_code == 201
    design = Design.objects.get()
    assert submission(client, admin_key, title="Ignored retry").status_code == 200
    design.refresh_from_db()
    assert design.title == "Warm editorial reference"
    design.published = False
    design.save()
    changed = {
        "frameworks": ["Vue"],
        "pricing": [
            {"billing": "recurring", "amount": "10", "currency": "USD", "interval": "month"}
        ],
    }
    with patch("apps.catalogue.ingestion.upsert_vector", side_effect=RuntimeError):
        assert (
            submission(client, admin_key, replace_existing=True, library=changed).status_code == 503
        )
    design.refresh_from_db()
    assert design.ui_library.frameworks == ["React"]
    assert submission(client, admin_key, replace_existing=True, library=changed).status_code == 200
    design.refresh_from_db()
    assert not design.published
    assert design.ui_library.frameworks == ["Vue"]
    user.is_superuser = False
    user.save()
    assert submission(client, admin_key).status_code == 401


@pytest.mark.parametrize(
    "metadata",
    [
        {"github_url": "javascript:alert(1)"},
        {"github_url": "https://github.com.evil.test/owner/repo"},
        {"pricing": [{"billing": "recurring", "amount": "10", "currency": "USD"}]},
        {"pricing": [{"billing": "one_time", "amount": "-1", "currency": "USD"}]},
        {"pricing": [{"billing": "free", "amount": "10", "currency": "USD"}]},
        {"frameworks": [""]},
    ],
)
def test_bad_library_metadata_rejected(client, admin_key, metadata):
    assert submission(client, admin_key, library=metadata).status_code == 422
    assert not Design.objects.exists()


def test_library_arena_disabled_including_existing_tokens(client, user, admin_key, qdrant_store):
    from apps.catalogue.arena import ArenaError, choose_pair, pair_token, submit_comparison
    from apps.catalogue.models import ArenaBallot, ArenaGuest

    submission(client, admin_key)
    submission(client, admin_key, source_url="https://example.org/")
    pair = list(Design.objects.filter(kind="ui_library"))
    for voter in [user, ArenaGuest.objects.create()]:
        assert not choose_pair(voter, 0, "ui_library")
        with pytest.raises(ArenaError, match="no longer available"):
            submit_comparison(voter, pair_token(voter, 0, pair), str(pair[0].pk))
    assert not ArenaBallot.objects.exists()
    assert client.get("/arena/?kind=ui_library").url == "/ui-libraries/"
    assert client.get("/rankings/?kind=ui_library").url == "/ui-libraries/"
    assert not client.get("/arena/").context["pair"]


def test_generic_design_endpoint_cannot_create_library(client, admin_key):
    files = bundle(kind="ui_library")
    assert client.post("/api/v1/designs", files, HTTP_X_API_KEY=admin_key).status_code == 422


def test_library_votes_do_not_personalize_landing_pages(client, user, admin_key, qdrant_store):
    from apps.catalogue.arena import ranked_designs
    from apps.catalogue.models import ArenaBallot
    from apps.catalogue.tests.test_ingestion import submit

    submission(client, admin_key)
    submission(client, admin_key, source_url="https://example.org/")
    pair = list(Design.objects.filter(kind="ui_library"))
    a, b = sorted(d.pk for d in pair)
    ArenaBallot.objects.create(user=user, design_a=a, design_b=b, winner=a)
    submit(client, admin_key, bundle())
    designs, summary = ranked_designs(user, "personal", "landing_page")
    assert len(designs) == 1
    assert not summary["has_taste"]


def test_library_name_alias_framework_search_and_escaped_notes(client, admin_key, qdrant_store):
    response = submission(
        client,
        admin_key,
        name="Example UI",
        library={"frameworks": ["Svelte"], "notes": "<script>alert(1)</script>"},
    )
    assert response.status_code == 201
    design = Design.objects.get()
    assert design.title == "Example UI"
    page = client.get(design.get_absolute_url()).content.decode()
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page
    assert client.get("/ui-libraries/?q=svelte").context["page"].paginator.count == 1
    assert client.get("/ui-libraries/?q=react").context["page"].paginator.count == 0
