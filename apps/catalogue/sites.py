"""Explicit site identity; no source fetching or inferred company matching."""

from urllib.parse import urlsplit, urlunsplit

from apps.catalogue.models import Site
from apps.catalogue.providers import public_url


def prepare_site(data):
    if data is None:
        return None
    parts = urlsplit(public_url(data["url"]))
    # One identity per origin. Paths/fragments never create separate companies.
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    if parts.port and parts.port != {"http": 80, "https": 443}[parts.scheme]:
        host = f"{host}:{parts.port}"
    url = urlunsplit((parts.scheme.lower(), host, "/", "", ""))
    return {"url": url, "name": data["name"]}


def resolve_site(data):
    if data is None:
        return None
    return Site.objects.get_or_create(url=data["url"], defaults={"name": data["name"]})[0]
