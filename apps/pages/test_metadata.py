from html.parser import HTMLParser

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.templatetags.static import static
from PIL import Image


class HeadMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = attrs.get("name") or attrs.get("property") or attrs.get("rel")
        if tag in {"meta", "link"} and key:
            self.tags.setdefault(key, []).append(attrs.get("content") or attrs.get("href"))


def test_homepage_preview_metadata_is_consistent_without_changing_other_pages():
    context = {
        "user": AnonymousUser(),
        "designs": [],
        "public_site_url": "https://tastefulkit.com",
    }
    rendered = render_to_string("pages/landing-page.html", context)
    head = HeadMetadata()
    head.feed(rendered)
    description = head.tags["description"]
    assert len(description) == 1
    assert "landing pages" in description[0]
    assert head.tags["og:description"] == head.tags["twitter:description"] == description
    assert len(head.tags["og:title"]) == 1
    assert head.tags["og:title"] == head.tags["twitter:title"]
    assert "Landing Page Inspiration" in head.tags["og:title"][0]
    assert head.tags["canonical"] == ["https://tastefulkit.com/"]
    assert head.tags["og:url"] == ["https://tastefulkit.com/"]
    assert head.tags["robots"] == ["index, follow"]
    assert rendered.count("<h1>") == 1

    for template in ("pages/privacy-policy.html", "catalogue/library.html"):
        other = HeadMetadata()
        other.feed(render_to_string(template, context))
        assert other.tags.get("description") != description
        if template.startswith("catalogue/"):
            assert "noindex" in other.tags["robots"][0]


def test_arena_has_a_public_stable_preview_independent_of_the_current_pair():
    context = {
        "user": AnonymousUser(),
        "public_site_url": "https://tastefulkit.com",
    }
    head = HeadMetadata()
    head.feed(render_to_string("catalogue/arena.html", context))

    assert head.tags["og:title"] == head.tags["twitter:title"] == ["Design Arena | TastefulKit"]
    assert (
        head.tags["og:description"] == head.tags["twitter:description"] == head.tags["description"]
    )
    assert head.tags["og:url"] == head.tags["canonical"] == ["https://tastefulkit.com/arena/"]
    assert (
        head.tags["og:image"]
        == head.tags["twitter:image"]
        == ["https://tastefulkit.com" + static("brand/arena-social-preview.png")]
    )
    assert head.tags["og:image:alt"] == head.tags["twitter:image:alt"]
    assert head.tags["og:image:alt"][0]
    assert head.tags["twitter:card"] == ["summary_large_image"]
    assert head.tags["robots"] == ["noindex, nofollow"]

    with Image.open(settings.BASE_DIR / "frontend/static/brand/arena-social-preview.png") as image:
        assert image.format == "PNG"
        assert head.tags["og:image:type"] == ["image/png"]
        assert image.size == (2400, 1260)
        assert head.tags["og:image:width"] == [str(image.width)]
        assert head.tags["og:image:height"] == [str(image.height)]
