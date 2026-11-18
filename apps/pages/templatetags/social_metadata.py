from django import template
from django.urls import reverse

from apps.pages import social

register = template.Library()


@register.inclusion_tag("components/page_metadata.html")
def page_metadata(key):
    return social.page_metadata(key)


@register.inclusion_tag("components/page_metadata.html")
def docs_metadata(category, page):
    return social.docs_metadata(category, page)


@register.inclusion_tag("components/page_metadata.html")
def design_metadata(pk, title, review_summary=""):
    return social.metadata(
        f"{title} | TastefulKit",
        review_summary
        or f"Explore {title}, a public landing page design reference on TastefulKit.",
        reverse("design_detail", args=[pk]),
        reverse("design_social_image", args=[pk]),
        alt=f"{title} landing page preview, curated by TastefulKit",
        robots="index, follow" if review_summary else "noindex",
    )
