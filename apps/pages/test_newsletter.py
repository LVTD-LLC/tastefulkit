from unittest.mock import Mock, patch

import pytest
import requests
from django.core.cache import cache
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def newsletter_settings(settings):
    cache.clear()
    settings.NEWSLETTER_LISTMONK_URL = "http://listmonk:9000"
    settings.NEWSLETTER_LIST_UUID = "list-uuid"


def test_landing_signup_and_filtered_catalog(client):
    html = client.get("/").content.decode()
    assert 'action="/newsletter/"' in html
    assert "weekly selection" in html
    assert 'type="email"' in html


@patch("apps.pages.newsletter.requests.post")
def test_signup_uses_public_double_optin_not_admin_api(post, client):
    post.return_value = Mock(status_code=200)
    post.return_value.json.return_value = {"data": {"has_optin": True}}
    response = client.post("/newsletter/", {"email": "reader@example.com"})
    assert response.status_code == 302
    assert response.url == "/newsletter/thanks/"
    post.assert_called_once_with(
        "http://listmonk:9000/api/public/subscription",
        json={"email": "reader@example.com", "list_uuids": ["list-uuid"]},
        timeout=(3, 10),
        allow_redirects=False,
    )


@patch("apps.pages.newsletter.requests.post")
def test_invalid_email_and_honeypot_do_not_send(post, client):
    assert client.post("/newsletter/", {"email": "invalid"}).status_code == 400
    assert (
        client.post("/newsletter/", {"email": "bot@example.com", "company": "spam"}).status_code
        == 302
    )
    post.assert_not_called()


@patch("apps.pages.newsletter.requests.post")
@pytest.mark.parametrize("failure", [requests.Timeout(), "http", "json", "shape"])
def test_provider_failures_do_not_claim_success(post, client, failure):
    post.return_value = Mock(status_code=200)
    if isinstance(failure, Exception):
        post.side_effect = failure
    elif failure == "http":
        post.return_value.status_code = 503
    elif failure == "json":
        post.return_value.json.side_effect = ValueError()
    else:
        post.return_value.json.return_value = {"data": False}
    response = client.post("/newsletter/", {"email": "reader@example.com"})
    assert response.status_code == 503
    assert b"try again" in response.content


@patch("apps.pages.newsletter.requests.post")
def test_repeat_signup_has_same_response(post, client):
    post.return_value = Mock(status_code=200)
    post.return_value.json.return_value = {"data": {"has_optin": False}}
    assert client.post("/newsletter/", {"email": "reader@example.com"}).status_code == 302


@patch("apps.pages.newsletter.requests.post")
def test_rate_limit_is_bounded(post, client):
    post.return_value = Mock(status_code=200)
    post.return_value.json.return_value = {"data": {"has_optin": True}}
    for _ in range(10):
        assert client.post("/newsletter/", {"email": "reader@example.com"}).status_code == 302
    response = client.post("/newsletter/", {"email": "reader@example.com"})
    assert response.status_code == 429
    assert response["Retry-After"] == "3600"
    assert post.call_count == 10


def test_disabled_newsletter_hides_form_and_rejects_post(client, settings):
    settings.NEWSLETTER_LIST_UUID = ""
    assert b'action="/newsletter/"' not in client.get("/").content
    assert client.post("/newsletter/", {"email": "reader@example.com"}).status_code == 503


def test_csrf_required():
    assert (
        Client(enforce_csrf_checks=True)
        .post("/newsletter/", {"email": "reader@example.com"})
        .status_code
        == 403
    )


@pytest.mark.parametrize(
    "kind",
    [
        "landing_page",
        "hero",
        "cta",
        "auth_form",
        "pricing_page",
        "navigation",
        "footer",
        "dashboard",
        "blog",
        "other",
    ],
)
def test_reference_detail_has_shared_signup(client, django_user_model, kind):
    from apps.catalogue.models import Design

    owner = django_user_model.objects.create_user(username="curator")
    design = Design.objects.create(
        title="Example",
        source_url="https://example.com",
        fingerprint=kind,
        kind=kind,
        capture_status="ready",
        screenshot="screenshot.png",
        thumbnail="thumbnail.png",
        submitted_by=owner,
    )
    response = client.get(design.get_absolute_url())
    assert response.status_code == 200
    assert response.content.count(b'action="/newsletter/"') == 1
    assert b'name="csrfmiddlewaretoken"' in response.content


@patch("apps.pages.newsletter.requests.post")
def test_limiter_failure_never_sends(post, client):
    with patch("apps.pages.newsletter.cache.add", side_effect=ConnectionError):
        assert client.post("/newsletter/", {"email": "reader@example.com"}).status_code == 429
    post.assert_not_called()


@patch("apps.pages.newsletter.requests.post")
def test_untrusted_headers_cannot_bypass_limit(post, client):
    post.return_value = Mock(status_code=200)
    post.return_value.json.return_value = {"data": {"has_optin": True}}
    for index in range(10):
        client.post("/newsletter/", {"email": "reader@example.com"}, HTTP_X_REAL_IP=str(index))
    assert (
        client.post(
            "/newsletter/", {"email": "reader@example.com"}, HTTP_X_REAL_IP="new"
        ).status_code
        == 429
    )
    assert post.call_count == 10


def test_bound_email_not_in_markdown(client):
    response = client.post("/newsletter/", {"email": "invalid"}, HTTP_ACCEPT="text/markdown")
    assert response["Content-Type"].startswith("text/html")
    assert "no-store" in response["Cache-Control"]


def test_ui_library_detail_has_signup(client, django_user_model):
    from apps.catalogue.models import Design, UILibrary

    owner = django_user_model.objects.create_user(username="curator")
    design = Design.objects.create(
        title="UI library",
        source_url="https://example.com",
        fingerprint="ui-library",
        kind="ui_library",
        capture_status="ready",
        screenshot="screenshot.png",
        thumbnail="thumbnail.png",
        submitted_by=owner,
    )
    UILibrary.objects.create(design=design, website_url="https://example.com")
    response = client.get(f"/ui-libraries/{design.pk}/")
    assert response.status_code == 200
    assert response.content.count(b'action="/newsletter/"') == 1
