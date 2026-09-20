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
def design_metadata(pk, title):
    return social.metadata(
        f"{title} | TastefulKit",
        (
            f"Explore {title}, a landing page design reference on TastefulKit. "
            "Join to view the full screenshot and design guide when available."
        ),
        reverse("design_detail", args=[pk]),
        reverse("design_social_image", args=[pk]),
        alt=f"{title} landing page preview, curated by TastefulKit",
        robots="noindex",
    )
