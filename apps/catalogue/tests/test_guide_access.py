from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.billing.models import BillingAccount
from apps.catalogue.models import Design
from apps.catalogue.services import serialize_design

pytestmark = pytest.mark.django_db
GUIDE = "# Paid-only guide\nUnique guide text that must not leak to free accounts."


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
    "status,days,cancel_at_period_end,allowed",
    [
        (None, 0, False, False),
        ("active", 30, False, True),
        ("active", 30, True, True),
        ("active", -1, False, False),
        ("canceled", 30, False, False),
        ("past_due", 30, False, False),
        ("trialing", 30, False, False),
        ("unpaid", 30, False, False),
    ],
)
def test_guide_access_across_html_download_and_rest(
    client, user, guide_design, status, days, cancel_at_period_end, allowed
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
    assert (GUIDE in html) == allowed
    assert ('id="design-markdown"' in html) == allowed
    assert ("Copy DESIGN.md" in html) == allowed
    assert ("Download DESIGN.md" in html) == allowed
    assert ("Unlock design guides" in html) != allowed
    download = client.get(reverse("design_markdown", args=[guide_design.pk]))
    assert "no-store" in download["Cache-Control"]
    if allowed:
        assert download.status_code == 200 and download.content.decode() == GUIDE
    else:
        assert download.status_code == 302 and download.url == "/pricing/"
        assert GUIDE not in download.content.decode()
    for header in ["HTTP_X_API_KEY", "HTTP_AUTHORIZATION"]:
        auth = {header: key if header == "HTTP_X_API_KEY" else f"Bearer {key}"}
        detail = client.get(f"/api/v1/designs/{guide_design.pk}", **auth)
        assert detail.status_code == 200
        assert detail["Cache-Control"] == "private, no-store"
        assert detail.json()["design_markdown"] == (GUIDE if allowed else None)
        assert detail.json()["design_markdown_locked"] is not allowed
        assert detail.json()["screenshot_url"].endswith("free-screenshot.png")
        listing = client.get("/api/v1/designs", **auth)
        assert listing.status_code == 200
        assert "design_markdown" not in listing.json()["items"][0]
    assert client.get("/explore/").status_code == 200
    assert client.get("/rankings/?mode=personal").status_code == 200
    assert client.post(reverse("save_design", args=[guide_design.pk])).status_code == 302


def test_missing_or_hidden_guides_are_not_sellable(client, user, guide_design):
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


def test_serializer_does_not_include_guide_without_explicit_entitlement(guide_design):
    result = serialize_design(guide_design, detail=True)
    assert result["design_markdown"] is None
    assert result["design_markdown_locked"] is True
