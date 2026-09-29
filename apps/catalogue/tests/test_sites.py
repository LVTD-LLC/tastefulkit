from unittest.mock import patch

import pytest

from apps.catalogue.models import Design
from apps.catalogue.tests.test_ingestion import bundle, submit


@pytest.fixture
def admin_key(user):
    user.is_superuser = True
    user.save()
    return user.profile.rotate_api_key()


pytestmark = pytest.mark.django_db


def test_site_groups_components_and_keeps_optional(client, user, admin_key, qdrant_store):
    site = {"name": "Example", "url": "https://example.com/"}
    first = submit(client, admin_key, bundle(site=site))
    assert first.status_code == 201, first.content
    second = submit(client, admin_key, bundle(site=site, kind="hero", selector="#hero"))
    assert second.status_code == 201, second.content
    assert first.json()["site"] == second.json()["site"]
    site_id = first.json()["site"]["id"]
    assert (
        client.get(f"/api/v1/designs?site={site_id}", HTTP_X_API_KEY=admin_key).json()["total"] == 2
    )
    detail = client.get(f"/api/v1/designs/{first.json()['id']}", HTTP_X_API_KEY=admin_key).json()
    assert [d["id"] for d in detail["related_designs"]] == [second.json()["id"]]
    client.force_login(user)
    html = client.get(f"/designs/{first.json()['id']}/").content.decode()
    assert "More from Example" in html
    assert 'class="tk-shot-viewport"' in html
    assert [str(d.pk) for d in client.get("/explore/?kind=hero").context["page"]] == [
        second.json()["id"]
    ]
    assert "Hero" in [item["label"] for item in client.get("/explore/").context["discovery_types"]]
    assert "Call to action" not in [
        item["label"] for item in client.get("/explore/").context["discovery_types"]
    ]
    Design.objects.filter(pk=second.json()["id"]).update(published=False)
    assert "Hero" not in [
        item["label"] for item in client.get("/explore/").context["discovery_types"]
    ]
    assert (
        client.get(f"/api/v1/designs/{first.json()['id']}", HTTP_X_API_KEY=admin_key).json()[
            "related_designs"
        ]
        == []
    )
    third = submit(client, admin_key, bundle(kind="auth_form", selector="#auth"))
    assert third.status_code == 201 and third.json()["site"] is None


def test_site_link_existing_preserves_assets_and_requires_admin(
    client, user, admin_key, qdrant_store
):
    first = submit(client, admin_key).json()
    url = f"/api/v1/designs/{first['id']}/site"
    with patch("apps.catalogue.sites.public_url", side_effect=lambda value: value):
        response = client.patch(
            url,
            {"site": {"name": "Example", "url": "https://EXAMPLE.com/path"}},
            content_type="application/json",
            HTTP_X_API_KEY=admin_key,
        )
    assert response.status_code == 200, response.content
    assert response.json()["site"]["url"] == "https://example.com/"
    assert response.json()["screenshot_url"] == first["screenshot_url"]
    user.is_superuser = False
    user.save()
    assert (
        client.patch(
            url, {"site": None}, content_type="application/json", HTTP_X_API_KEY=admin_key
        ).status_code
        == 401
    )


def test_replacement_omission_preserves_site_null_clears_and_failures_rollback(
    client, admin_key, qdrant_store
):
    from apps.catalogue.models import Site

    site = {"name": "Example", "url": "https://example.com/"}
    first = submit(client, admin_key, bundle(site=site)).json()
    replaced = submit(client, admin_key, bundle(replace_existing=True)).json()
    assert replaced["site"] == first["site"]
    with (
        patch("apps.catalogue.ingestion.upsert_vector", side_effect=TimeoutError),
        patch("apps.catalogue.sites.public_url", side_effect=lambda value: value),
    ):
        assert (
            submit(
                client,
                admin_key,
                bundle(kind="cta", site={"name": "Other", "url": "https://other.example/"}),
            ).status_code
            == 503
        )
    assert Site.objects.count() == 1
    cleared = submit(client, admin_key, bundle(replace_existing=True, site=None)).json()
    assert cleared["site"] is None


@pytest.mark.parametrize(
    "site",
    [
        {"name": " ", "url": "https://example.com"},
        {"name": "Bad", "url": "javascript:alert(1)"},
        {"name": "Bad", "url": "http://127.0.0.1"},
    ],
)
def test_invalid_sites_rejected(client, admin_key, site):
    assert submit(client, admin_key, bundle(site=site)).status_code == 422
    assert not Design.objects.exists()
