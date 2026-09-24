"""Use the same revocable, hashed personal API keys as the REST API."""

from contextlib import contextmanager

from asgiref.sync import sync_to_async
from django.db import close_old_connections, connections
from django.http import Http404
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token

from apps.api.auth import get_profile_for_api_key
from tastefulkit.logging_utils import bind_log_context, reset_log_context


@contextmanager
def database_scope():
    # Neither Django's request connection cleanup nor log middleware runs in MCP.
    context = bind_log_context()
    close_old_connections()
    try:
        yield
    finally:
        connections.close_all()
        reset_log_context(context)


def verify_api_key(token):
    with database_scope():
        profile = get_profile_for_api_key(token)
        if profile is None:
            return None
        return AccessToken(token=token, client_id=str(profile.pk), scopes=[])


class APIKeyVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        return await sync_to_async(verify_api_key, thread_sensitive=True)(token)


@contextmanager
def authenticated_profile(*, admin=False):
    """Fail closed even for in-memory transports; never accept tool-supplied identity."""
    with database_scope():
        access_token = get_access_token()
        profile = get_profile_for_api_key(access_token.token) if access_token else None
        if profile is None:
            raise ToolError("A valid API key for an active TastefulKit account is required.")
        if admin and not profile.user.is_superuser:
            raise ToolError("Administrator access is required.")
        try:
            yield profile
        except Http404:
            raise ToolError("Design not found or not available to your account.") from None
        except ValueError as exc:
            raise ToolError(str(exc)) from None
