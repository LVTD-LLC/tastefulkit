"""Outbound rendering happens at Cloudflare, never inside the application network."""

import ipaddress
import json
import math
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

EMBEDDING_MODEL = "@cf/baai/bge-base-en-v1.5"


def public_url(value):
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Use a complete public HTTP or HTTPS URL.")
    if parts.username or parts.password or parts.port not in {None, 80, 443}:
        raise ValueError("Credentials and non-standard ports are not allowed in source URLs.")
    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as exc:
        raise ValueError("The source hostname could not be resolved.") from exc
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Only public Internet websites can be captured.")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, "")
    )


def cloudflare_request(path, payload, *, binary=False):
    if not settings.CF_RENDER_TOKEN or not settings.CF_ACCOUNT_ID:
        raise ValueError("Screenshot and embedding provider is not configured.")
    request = Request(
        f"https://api.cloudflare.com/client/v4/accounts/{settings.CF_ACCOUNT_ID}/{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.CF_RENDER_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=55 if binary else 12) as response:
            content = response.read(20 * 1024 * 1024 + 1)
    except HTTPError as exc:
        raise ValueError(
            f"Cloudflare returned HTTP {exc.code}; retry or check provider access."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("Cloudflare did not respond in time. Retry this entry.") from None
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("Provider response exceeded the 20 MB limit.")
    if binary:
        return content
    result = json.loads(content)
    if not result.get("success"):
        raise ValueError("The embedding provider could not complete this request.")
    return result["result"]


def capture(design):
    payload = {
        "url": public_url(design.source_url),
        "viewport": {"width": design.viewport_width, "height": 900},
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": 40000},
        "screenshotOptions": {"fullPage": True, "type": "jpeg", "quality": 82},
    }
    if design.selector:
        payload["selector"] = design.selector
    return cloudflare_request("browser-rendering/screenshot", payload, binary=True)


def embed(text):
    import hashlib

    key = "embedding:" + hashlib.sha256((EMBEDDING_MODEL + text).encode()).hexdigest()
    if (cached := cache.get(key)) is not None:
        return cached
    result = cloudflare_request(f"ai/run/{EMBEDDING_MODEL}", {"text": [text[:6000]]})
    vector = result["data"][0]
    if len(vector) != 768 or any(not math.isfinite(float(v)) for v in vector):
        raise ValueError("The embedding provider returned an invalid vector.")
    cache.set(key, vector, 3600)
    return vector
