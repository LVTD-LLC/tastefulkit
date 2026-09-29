from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.billing.models import BillingAccount
from apps.catalogue.models import Design
from apps.catalogue.services import serialize_design

pytestmark = pytest.mark.django_db
GUIDE = "# Free design guide\nAvailable to every active account."


@pytest.fixture
def guide_design(user):
    return Design.objects.create(
        title="Free screenshot reference",
        source_url="https://example.com/",
        description="Public reference metadata",
        fingerprint="paid-guide-reference",
        submitted_by=user,
        capture_status="ready",
        screenshot="free-screenshot.png",
        thumbnail="free-thumbnail.png",
        design_markdown=GUIDE,
    )


@pytest.mark.parametrize(
    "status,days,cancel_at_period_end",
    [
        (None, 0, False),
        ("active", 30, False),
        ("active", 30, True),
        ("active", -1, False),
        ("canceled", 30, False),
        ("past_due", 30, False),
        ("trialing", 30, False),
        ("unpaid", 30, False),
    ],
)
def test_guide_access_across_html_download_and_rest(
    client, user, guide_design, status, days, cancel_at_period_end
):
    if status is not None:
        BillingAccount.objects.create(
            user=user,
            status=status,
            paid_until=timezone.now() + timedelta(days=days),
            cancel_at_period_end=cancel_at_period_end,
        )
    key = user.profile.rotate_api_key()
    client.force_login(user)
    page = client.get(guide_design.get_absolute_url())
    assert page.status_code == 200
    assert "no-store" in page["Cache-Control"]
    html = page.content.decode()
    assert "free-screenshot.png" in html
    assert "Public reference metadata" in html
    assert GUIDE in html
    assert 'id="design-markdown"' in html
    assert "Copy DESIGN.md" in html
    assert "Download DESIGN.md" in html
    assert "Unlock design guides" not in html
    download = client.get(reverse("design_markdown", args=[guide_design.pk]))
    assert "no-store" in download["Cache-Control"]
    assert download.status_code == 200 and download.content.decode() == GUIDE
    for header in ["HTTP_X_API_KEY", "HTTP_AUTHORIZATION"]:
        auth = {header: key if header == "HTTP_X_API_KEY" else f"Bearer {key}"}
        detail = client.get(f"/api/v1/designs/{guide_design.pk}", **auth)
        assert detail.status_code == 200
        assert detail["Cache-Control"] == "private, no-store"
        assert detail.json()["design_markdown"] == GUIDE
        assert detail.json()["design_markdown_locked"] is False
        assert detail.json()["screenshot_url"].endswith("free-screenshot.png")
        listing = client.get("/api/v1/designs", **auth)
        assert listing.status_code == 200
        assert "design_markdown" not in listing.json()["items"][0]
    assert client.get("/explore/").status_code == 200
    assert client.get("/rankings/?mode=personal").status_code == 200
    assert client.post(reverse("save_design", args=[guide_design.pk])).status_code == 302


def test_missing_or_hidden_guides_remain_unavailable(client, user, guide_design):
    client.force_login(user)
    guide_design.design_markdown = ""
    guide_design.save()
    assert b"Unlock design guides" not in client.get(guide_design.get_absolute_url()).content
    assert client.get(reverse("design_markdown", args=[guide_design.pk])).status_code == 404
    key = user.profile.rotate_api_key()
    detail = client.get(f"/api/v1/designs/{guide_design.pk}", HTTP_X_API_KEY=key).json()
    assert detail["design_markdown"] is None
    assert detail["design_markdown_locked"] is False
    guide_design.published = False
    guide_design.save()
    assert client.get(guide_design.get_absolute_url()).status_code == 404
    assert client.get(reverse("design_markdown", args=[guide_design.pk])).status_code == 404
    assert client.get(f"/api/v1/designs/{guide_design.pk}", HTTP_X_API_KEY=key).status_code == 404


def test_serializer_requires_explicit_guide_inclusion(guide_design):
    result = serialize_design(guide_design, detail=True)
    assert result["design_markdown"] is None
    assert result["design_markdown_locked"] is True


def test_guides_still_require_an_active_account(client, user, guide_design):
    path = reverse("design_markdown", args=[guide_design.pk])
    assert "/accounts/login/" in client.get(path).url
    key = user.profile.rotate_api_key()
    user.is_active = False
    user.save()
    assert client.get(f"/api/v1/designs/{guide_design.pk}", HTTP_X_API_KEY=key).status_code == 401
    client.force_login(user)
    assert "/accounts/login/" in client.get(path).url
    assert GUIDE not in client.get(guide_design.get_absolute_url()).content.decode()
