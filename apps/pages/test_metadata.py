from html.parser import HTMLParser

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string


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
