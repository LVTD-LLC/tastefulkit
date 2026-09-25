"""Publication visibility and metadata stay consistent across all public surfaces."""

import json
from datetime import date
from pathlib import Path

import frontmatter
import pytest
from django.conf import settings

from apps.pages import blog
from apps.pages.test_metadata import HeadMetadata


@pytest.fixture
def content_root(tmp_path, monkeypatch):
    monkeypatch.setattr(blog, "BLOG_CONTENT_ROOT", tmp_path)
    monkeypatch.setattr(blog.timezone, "localdate", lambda: date(2026, 9, 20))
    return tmp_path


def write_post(root, slug="sample-guide", **metadata):
    values = {
        "title": "Choose a reference",
        "description": "A concrete design-reference workflow.",
        "author": "TastefulKit",
        "date": "2026-09-18",
        **metadata,
    }
    path = root / f"{slug}.md"
    path.write_text(
        frontmatter.dumps(
            frontmatter.Post(
                "An introduction.\n\n## Compare references\n\nChoose the page's structure.\n\n"
                "### Check small screens\n\n[Try the arena](/arena/).",
                **values,
            )
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    "changes",
    [
        {"title": ""},
        {"description": None},
        {"author": 42},
        {"date": "not-a-date"},
        {"date": "2026-02-30"},
        {"date": "20260918"},
        {"date": "2026-09-18T12:00:00Z"},
        {"updated": "2026-09-17"},
        {"draft": "false"},
    ],
)
def test_invalid_metadata_is_rejected(content_root, changes):
    path = write_post(content_root, **changes)
    with pytest.raises(ValueError):
        blog.load_post(path)
    assert blog.published_posts() == []


def test_missing_required_fields_and_empty_body_are_rejected(content_root):
    path = write_post(content_root)
    for field in ("date", "title", "author", "description"):
        document = frontmatter.load(path)
        document.metadata.pop(field)
        path.write_text(frontmatter.dumps(document), encoding="utf-8")
        with pytest.raises(ValueError):
            blog.load_post(path)
        write_post(content_root)
    document = frontmatter.load(path)
    document.content = ""
    path.write_text(frontmatter.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError):
        blog.load_post(path)


def test_publication_filter_sorting_and_dates(content_root):
    write_post(content_root, "older", date="2026-09-17", updated="2026-09-19")
    write_post(content_root, "newer", date="2026-09-18")
    write_post(content_root, "draft", draft=True)
    write_post(content_root, "future", date="2026-09-21")
    write_post(content_root, "future-update", updated="2026-09-21")
    write_post(content_root, "Wrong_Slug")
    (content_root / "broken-yaml.md").write_text("---\ntitle: [\n---\nbody")
    posts = blog.published_posts()
    assert [post.slug for post in posts] == ["newer", "older"]
    assert posts[0].updated == posts[0].published == date(2026, 9, 18)
    assert posts[1].updated == date(2026, 9, 19)


@pytest.mark.django_db
def test_index_article_related_links_and_sitemap_agree(client, settings, content_root):
    settings.SITE_URL = "https://tastefulkit.com"
    settings.POSTHOG_API_KEY = "phc_test"
    write_post(content_root, "sample-guide", updated="2026-09-19")
    write_post(content_root, "other-guide")
    write_post(content_root, "draft-secret", draft=True)
    write_post(content_root, "future-secret", date="2026-09-21")
    write_post(content_root, "bad-secret", author=None)
    homepage = client.get("/")
    assert homepage.status_code == 200
    assert 'href="/blog/sample-guide/"' in homepage.content.decode()
    assert "draft-secret" not in homepage.content.decode()
    index = client.get("/blog/")
    assert index.status_code == 200
    assert 'href="/blog/sample-guide/"' in index.content.decode()
    assert 'href="/blog/other-guide/"' in index.content.decode()
    article = client.get("/blog/sample-guide/?utm_source=test")
    assert article.status_code == 200
    html = article.content.decode()
    assert 'data-posthog-public-content-path="/blog/sample-guide/"' in html
    assert 'data-posthog-route="/blog/:slug/"' in html
    assert "data-posthog-public-content-path" not in index.content.decode()
    assert html.count("<h1>") == 1
    assert 'href="#compare-references"' in html
    assert 'id="compare-references"' in html
    assert 'href="/blog/other-guide/"' in html
    assert 'datetime="2026-09-19"' in html
    assert "Updated" in html
    head = HeadMetadata()
    head.feed(html)
    assert head.tags["robots"] == ["index, follow"]
    assert (
        head.tags["canonical"]
        == head.tags["og:url"]
        == ["https://tastefulkit.com/blog/sample-guide/"]
    )
    assert head.tags["og:title"] == head.tags["twitter:title"]
    assert (
        head.tags["description"] == head.tags["og:description"] == head.tags["twitter:description"]
    )
    assert head.tags["article:published_time"] == ["2026-09-18"]
    assert head.tags["article:modified_time"] == ["2026-09-19"]
    schema = json.loads(article.context["schema_json"])
    posting, breadcrumb = schema["@graph"]
    assert posting["datePublished"] == "2026-09-18"
    assert posting["dateModified"] == "2026-09-19"
    assert posting["mainEntityOfPage"] == head.tags["canonical"][0]
    assert breadcrumb["itemListElement"][-1]["item"] == head.tags["canonical"][0]
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    xml = sitemap.content.decode()
    assert "<loc>https://tastefulkit.com/blog/</loc>" in xml
    assert (
        "<loc>https://tastefulkit.com/blog/sample-guide/</loc><lastmod>2026-09-19</lastmod>" in xml
    )
    for slug in ("draft-secret", "future-secret", "bad-secret", "missing"):
        response = client.get(f"/blog/{slug}/")
        assert response.status_code == 404
        assert "data-posthog-public-content-path" not in response.content.decode()
        assert slug not in index.content.decode()
        assert slug not in html
        assert slug not in xml
        assert client.get(f"/blog/{slug}/").status_code == 404
    index_head = HeadMetadata()
    index_head.feed(index.content.decode())
    assert index_head.tags["canonical"] == ["https://tastefulkit.com/blog/"]


@pytest.mark.django_db
def test_empty_blog_is_public_and_navigable(client, content_root):
    response = client.get("/blog/")
    assert response.status_code == 200
    assert "Guides are on their way" in response.content.decode()
    assert 'href="/arena/"' in response.content.decode()
    assert response.content.decode().count('href="/blog/"') >= 3


@pytest.mark.django_db
def test_metadata_cannot_break_out_of_html_or_json_ld(client, content_root):
    title = 'Guide </script><script>alert("x")</script> & design'
    write_post(content_root, title=title)
    response = client.get("/blog/sample-guide/")
    html = response.content.decode()
    assert response.status_code == 200
    assert title not in html
    assert "\\u003C/script\\u003E" in html
    schema = json.loads(response.context["schema_json"])
    assert schema["@graph"][0]["headline"] == title


def test_repository_blog_content_has_valid_metadata():
    root = Path(settings.BASE_DIR) / "apps/pages/content/blog"
    for path in root.glob("*.md"):
        post = blog.load_post(path)
        assert post.body.strip(), path
        assert not any(line.startswith("# ") for line in post.body.splitlines()), path


@pytest.mark.django_db
def test_tables_and_fenced_code_are_keyboard_scrollable(client, content_root):
    path = write_post(content_root)
    document = frontmatter.load(path)
    document.content = """## Compare

| Reference | Decision |
| --- | --- |
| One & two | Keep the hierarchy |

```html
<table><tr><td>Not a real table</td></tr></table>
```
"""
    path.write_text(frontmatter.dumps(document), encoding="utf-8")
    response = client.get("/blog/sample-guide/")
    assert response.status_code == 200
    content = response.context["content"]
    assert content.count('class="tk-blog-scroll" tabindex="0" role="region"') == 2
    assert 'aria-label="Data table, scroll horizontally"><table>' in content
    assert 'aria-label="Code example, scroll horizontally"><pre>' in content
    assert "</table></div>" in content
    assert "</pre></div>" in content
    assert "One &amp; two" in content
    assert "&lt;table&gt;" in content
    assert '<code class="language-html">' in content
