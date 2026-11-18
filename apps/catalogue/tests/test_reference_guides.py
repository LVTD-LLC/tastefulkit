from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.catalogue.management.commands.reference_guides import apply_review
from apps.catalogue.models import Design

pytestmark = pytest.mark.django_db


def test_review_publication_and_visibility(client, user):
    summary = "Align the action with the left edge of the inset chart and keep its label short."
    guide = (
        "---\nname: Chart\ncolors: {ink: black}\ntypography: {display: sans}\n---\n## Layout\n"
        + summary
    )
    design = Design.objects.create(
        title="Chart",
        source_url="https://example.com/",
        description="Chart",
        submitted_by=user,
        capture_status="ready",
        screenshot="chart.png",
        design_markdown=guide,
    )
    row = {
        "id": str(design.pk),
        "updated_at": design.updated_at.isoformat(),
        "summary": summary,
        "design_markdown": guide,
    }
    detail = design.get_absolute_url()
    sitemap = reverse("django.contrib.sitemaps.views.sitemap")
    assert detail not in client.get(sitemap).content.decode()
    assert 'content="noindex"' in client.get(detail).content.decode()
    assert apply_review(row, write=False) == "validated"
    design.refresh_from_db()
    assert not design.review_summary
    assert apply_review(row, write=True) == "published"
    assert apply_review(row, write=True) == "unchanged"
    assert detail in client.get(sitemap).content.decode()
    html = client.get(detail).content.decode()
    assert 'content="index, follow"' in html and f"<p>{summary}</p>" in html
    assert client.get(reverse("design_markdown", args=[design.pk])).content.decode() == guide
    exported = StringIO()
    call_command("reference_guides", "export", stdout=exported)
    assert str(design.pk) not in exported.getvalue()
    with pytest.raises(ValueError, match="changed"):
        apply_review({**row, "design_markdown": guide + "\nExtra notes."}, write=True)
    design.published = False
    design.save(update_fields=["published"])
    assert detail not in client.get(sitemap).content.decode()
    assert client.get(detail).status_code == 404
    with pytest.raises(Design.DoesNotExist):
        apply_review(row, write=True)
