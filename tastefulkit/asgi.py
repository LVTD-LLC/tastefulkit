"""Django and authenticated Streamable HTTP MCP on one ASGI service."""

import os

from django.conf import settings
from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tastefulkit.settings")
django_application = get_asgi_application()

# Initialize Django before importing the server's model-backed services.
from apps.hosted_mcp.server import mcp  # noqa: E402

mcp_application = mcp.http_app(
    path="/",
    stateless_http=True,
    json_response=True,
    host_origin_protection=True,
    allowed_hosts=[value for host in settings.ALLOWED_HOSTS for value in (host, f"{host}:*")],
    allowed_origins=[settings.SITE_URL.rstrip("/")],
)


async def mcp_redirect(request):
    return RedirectResponse("/mcp/", status_code=307)


application = Starlette(
    routes=[
        Route("/mcp", mcp_redirect, methods=["GET", "POST", "DELETE", "OPTIONS"]),
        Mount("/mcp", app=mcp_application),
        Mount("/", app=django_application),
    ],
    lifespan=mcp_application.lifespan,
)
