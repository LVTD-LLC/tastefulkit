"""Public page metadata and a finite registry of shareable page cards."""

from hashlib import sha256

import frontmatter
from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_safe

from apps.pages.social_images import render_social_image

PAGES = {
    "landing": {
        "title": "Landing Page Inspiration for You & Your Agent | TastefulKit",
        "description": (
            "Find landing pages you love with personalized pairwise rankings, then give "
            "your coding agent the references to build from."
        ),
        "image": "brand/home-social-preview.png",
        "alt": (
            "TastefulKit: Find your taste. Build from it. Real landing page references "
            "from Raycast and Notion."
        ),
    },
    "voting_arena": {
        "title": "Design Arena | TastefulKit",
        "description": (
            "Compare real websites. Discover your taste. Vote on landing page designs for "
            "free in the TastefulKit Arena. No account needed."
        ),
        "image": "brand/arena-social-preview.png",
        "alt": "Design Arena: Raycast versus Notion in a fighting-game-style website matchup.",
        "robots": "noindex, nofollow",
    },
    "design_rankings": {
        "title": "Global design rankings | TastefulKit",
        "description": (
            "Explore the community's favorite landing pages, ranked by real comparisons "
            "in the Design Arena."
        ),
        "headline": "Good design.\nChosen together.",
        "label": "Global rankings",
        "robots": "noindex, nofollow",
    },
    "pricing": {
        "title": "Membership | TastefulKit",
        "description": (
            "Explore the landing page catalog, save references, discover your personal "
            "ranking, and connect your coding agent with a TastefulKit membership."
        ),
        "headline": "Your taste.\nYour next landing page.",
        "label": "Membership",
        "robots": "noindex",
    },
    "privacy_policy": {
        "title": "Privacy Policy | TastefulKit",
        "description": (
            "Learn how TastefulKit collects, uses, and protects your personal information."
        ),
        "headline": "Your privacy\nmatters.",
        "label": "Privacy policy",
    },
    "terms_of_service": {
        "title": "Terms of Service | TastefulKit",
        "description": "Read the terms and conditions for using TastefulKit.",
        "headline": "The terms.\nIn plain view.",
        "label": "Terms of service",
    },
    "uses": {
        "title": "Technology Stack | TastefulKit",
        "description": "The core technologies and services used by TastefulKit.",
        "headline": "What we're\nbuilt with.",
        "label": "Technology stack",
    },
    "account_login": {
        "title": "Sign in | TastefulKit",
        "description": "Sign in to your TastefulKit account.",
        "image": "brand/home-social-preview.png",
        "robots": "noindex, nofollow",
    },
    "account_signup": {
        "title": "Get started | TastefulKit",
        "description": (
            "Create your TastefulKit account and discover your taste in landing page design."
        ),
        "image": "brand/home-social-preview.png",
        "robots": "noindex, nofollow",
    },
}


def metadata(
    title, description, path, image_path, *, alt, width=1200, height=630, robots="index, follow"
):
    origin = settings.SITE_URL.rstrip("/")
    return {
        "title": title,
        "description": description,
        "canonical": origin + path,
        "image_url": origin + image_path,
        "image_alt": alt,
        "image_width": width,
        "image_height": height,
        "robots": robots,
    }


def page_metadata(key):
    page = PAGES[key]
    artwork = page.get("image")
    return metadata(
        page["title"],
        page["description"],
        reverse(key),
        static(artwork) if artwork else reverse("page_social_image", args=[key]),
        alt=page.get("alt", f"TastefulKit — {page.get('label', 'Landing page inspiration')}"),
        width=2400 if artwork else 1200,
        height=1260 if artwork else 630,
        robots=page.get("robots", "index, follow"),
    )


def document_info(category, page):
    # Look up only repository-tracked, navigable docs. No arbitrary filesystem paths.
    from apps.pages.views import DOCS_CONTENT_ROOT, get_docs_navigation, get_flat_page_list

    known = get_flat_page_list(get_docs_navigation())
    match = next(
        (item for item in known if item["category_slug"] == category and item["page_slug"] == page),
        None,
    )
    if match is None:
        raise Http404
    post = frontmatter.load(DOCS_CONTENT_ROOT / category / f"{page}.md")
    return match["page_title"], post.get(
        "description", ""
    ) or f"{match['page_title']} documentation for TastefulKit"


def docs_metadata(category, page):
    title, description = document_info(category, page)
    return metadata(
        f"{title} | TastefulKit Documentation",
        description,
        reverse("docs_page", args=[category, page]),
        reverse("docs_social_image", args=[category, page]),
        alt=f"TastefulKit documentation: {title}",
    )


def png_response(title, description, label):
    # Content-based keys refresh cards when the repository's copy changes.
    key = "social:1:" + sha256(repr((title, description, label)).encode()).hexdigest()
    content = cache.get(key)
    if content is None:
        content = render_social_image(title, description, label)
        cache.set(key, content, 3600)
    response = HttpResponse(content, content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_safe
def page_social_image(request, key):
    page = PAGES.get(key)
    if not page or "image" in page:
        raise Http404
    return png_response(page["headline"], page["description"], page["label"])


@require_safe
def docs_social_image(request, category, page):
    title, description = document_info(category, page)
    return png_response(title, description, "Documentation")
