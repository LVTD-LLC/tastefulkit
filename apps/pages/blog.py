"""Public, repository-managed blog content (no database or membership required)."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import frontmatter
import markdown
import yaml
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from apps.core.views import build_absolute_public_url

logger = logging.getLogger(__name__)
BLOG_CONTENT_ROOT = Path(settings.BASE_DIR) / "apps/pages/content/blog"
SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class BlogPost:
    slug: str
    title: str
    description: str
    author: str
    published: date
    updated: date
    body: str
    draft: bool = False
    roundup_items: tuple[tuple[str, str], ...] = ()
    related_slugs: tuple[str, ...] = ()

    @property
    def url(self):
        return reverse("blog_post", kwargs={"slug": self.slug})


def metadata_date(value):
    """Accept YAML dates or strict ISO date strings, never datetimes or loose dates."""
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value)
    raise ValueError("Blog dates must use YYYY-MM-DD")


def related_slugs(value, current_slug):
    """Validate editorial navigation without allowing external or duplicate targets."""
    if (
        not isinstance(value, list)
        or len(value) > 3
        or any(
            not isinstance(slug, str) or not SLUG_PATTERN.fullmatch(slug) or slug == current_slug
            for slug in value
        )
        or len(set(value)) != len(value)
    ):
        raise ValueError("Blog related guides need up to three unique other article slugs")
    return tuple(value)


def load_post(path):
    if not SLUG_PATTERN.fullmatch(path.stem):
        raise ValueError("Blog filenames must use lowercase, hyphenated slugs")
    with path.open(encoding="utf-8") as source:
        document = frontmatter.load(source)
    fields = {}
    for key in ("title", "description", "author"):
        value = document.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Blog {key} must be a nonempty string")
        fields[key] = value.strip()
    published = metadata_date(document.get("date"))
    updated = metadata_date(document.get("updated", published))
    if updated < published:
        raise ValueError("Blog updated date cannot precede publication")
    draft = document.get("draft", False)
    if not isinstance(draft, bool):
        raise ValueError("Blog draft must be a YAML boolean")
    if not document.content.strip():
        raise ValueError("Blog body cannot be empty")
    roundup_items = document.get("roundup_items", [])
    if not isinstance(roundup_items, list):
        raise ValueError("Blog roundup_items must be a list")
    validated_items = []
    for item in roundup_items:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("name"), str)
            or not item["name"].strip()
            or not isinstance(item.get("path"), str)
            or not re.fullmatch(r"/ui-libraries/[0-9a-f-]{36}/", item["path"])
            or item["path"] not in document.content
        ):
            raise ValueError("Roundup items need a name and a referenced library path")
        validated_items.append((item["name"].strip(), item["path"]))
    return BlogPost(
        path.stem,
        **fields,
        published=published,
        updated=updated,
        body=document.content,
        draft=draft,
        roundup_items=tuple(validated_items),
        related_slugs=related_slugs(document.get("related", []), path.stem),
    )


def published_posts():
    """One visibility rule for index, detail, related links, and sitemap."""
    today = timezone.localdate()
    posts = []
    for path in BLOG_CONTENT_ROOT.glob("*.md"):
        try:
            post = load_post(path)
        except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError) as error:
            logger.warning(
                "blog.content.load.completed",
                extra={
                    "event.name": "blog.content.load.completed",
                    "outcome": "failure",
                    "error.type": type(error).__name__,
                },
            )
            continue
        if not post.draft and post.published <= today and post.updated <= today:
            posts.append(post)
    return sorted(posts, key=lambda post: (post.published, post.slug), reverse=True)


def roundups_for_library(path):
    """Link only published guides that explicitly recommend this library."""
    return [
        post
        for post in published_posts()
        if any(item_path == path for _name, item_path in post.roundup_items)
    ]


def _metadata(title, description, path):
    return {
        "page_title": title,
        "meta_description": description,
        "canonical_url": build_absolute_public_url(path),
        "social_image_url": build_absolute_public_url(static("brand/social-preview.png")),
    }


def blog_index(request):
    context = _metadata(
        "Landing page design guides",
        "Practical guides to landing page inspiration, design references, and building "
        "with AI coding agents from TastefulKit.",
        reverse("blog_index"),
    )
    context["posts"] = published_posts()
    return render(request, "pages/blog/index.html", context)


def _post_schema(post, context):
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "@id": context["canonical_url"] + "#article",
                "headline": post.title,
                "description": post.description,
                "datePublished": post.published.isoformat(),
                "dateModified": post.updated.isoformat(),
                "author": {"@type": "Organization", "name": post.author},
                "publisher": {
                    "@type": "Organization",
                    "name": "TastefulKit",
                    "url": build_absolute_public_url("/"),
                },
                "mainEntityOfPage": context["canonical_url"],
                "image": context["social_image_url"],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": build_absolute_public_url("/"),
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Blog",
                        "item": build_absolute_public_url(reverse("blog_index")),
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": post.title,
                        "item": context["canonical_url"],
                    },
                ],
            },
        ],
    }
    if post.roundup_items:
        schema["@graph"].append(
            {
                "@type": "ItemList",
                "@id": context["canonical_url"] + "#shortlist",
                "name": post.title,
                "itemListOrder": "https://schema.org/ItemListUnordered",
                "numberOfItems": len(post.roundup_items),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": position,
                        "name": name,
                        "url": build_absolute_public_url(path),
                    }
                    for position, (name, path) in enumerate(post.roundup_items, 1)
                ],
            }
        )
    # Script elements do not honor HTML entities. Escape delimiters as JSON Unicode
    # sequences so metadata containing </script> can never terminate the element.
    return json.dumps(schema).translate(
        str.maketrans({"<": r"\u003C", ">": r"\u003E", "&": r"\u0026"})
    )


class ScrollRegions(HTMLParser):
    """Insert focusable wrappers without rewriting trusted Markdown-generated HTML."""

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_offsets = [0, *(match.end() for match in re.finditer("\n", source))]
        self.insertions = []
        self.open_regions = []

    def source_position(self):
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        labels = {
            "table": "Data table, scroll horizontally",
            "pre": "Code example, scroll horizontally",
        }
        if tag in labels:
            self.insertions.append(
                (
                    self.source_position(),
                    '<div class="tk-blog-scroll" tabindex="0" role="region" '
                    f'aria-label="{labels[tag]}">',
                )
            )
            self.open_regions.append(tag)

    def handle_endtag(self, tag):
        if self.open_regions and tag == self.open_regions[-1]:
            self.open_regions.pop()
            end = self.source.index(">", self.source_position()) + 1
            self.insertions.append((end, "</div>"))


def scrollable_content(source):
    parser = ScrollRegions(source)
    parser.feed(source)
    parser.close()
    for offset, insertion in reversed(parser.insertions):
        source = source[:offset] + insertion + source[offset:]
    return source


def blog_post(request, slug):
    posts = published_posts()
    post = next((post for post in posts if post.slug == slug), None)
    if post is None:
        raise Http404("Blog post not found")
    if post.related_slugs:
        visible_posts = {other.slug: other for other in posts}
        related_posts = [
            visible_posts[related] for related in post.related_slugs if related in visible_posts
        ]
    else:
        related_posts = [other for other in posts if other.slug != slug][:3]
    renderer = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc"], extension_configs={"toc": {"toc_depth": "2-3"}}
    )
    context = _metadata(post.title, post.description, post.url)
    context.update(
        {
            "post": post,
            # Only a validated, published repository article can supply this identity.
            "posthog_public_content_path": post.url,
            "content": scrollable_content(renderer.convert(post.body)),
            "related_posts": related_posts,
        }
    )
    context["toc"] = renderer.toc if renderer.toc_tokens else ""
    context["schema_json"] = _post_schema(post, context)
    return render(request, "pages/blog/post.html", context)
