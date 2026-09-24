import asyncio
import socket
import threading
import time
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
import uvicorn
from fastmcp import Client
from starlette.testclient import TestClient

from apps.catalogue.models import Design, Tag
from tastefulkit.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)
HEADERS = {"Accept": "application/json, text/event-stream"}


@pytest.fixture
def key(user):
    return user.profile.rotate_api_key()


@pytest.fixture
def design(user):
    design = Design.objects.create(
        title="Warm minimal website",
        source_url="https://example.com/",
        fingerprint="a" * 64,
        description="Warm typography and generous whitespace.",
        industry="Software",
        submitted_by=user,
        capture_status="ready",
        screenshot="shot.jpg",
        thumbnail="thumb.jpg",
    )
    design.tags.add(Tag.objects.create(name="minimal"))
    return design


@pytest.fixture
def http(key):
    with TestClient(application, headers={**HEADERS, "Authorization": f"Bearer {key}"}) as client:
        yield client


def rpc(http, method, params=None):
    response = http.post(
        "/mcp/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def call(http, name, **arguments):
    return rpc(http, "tools/call", {"name": name, "arguments": arguments})["result"]


def data(http, name, **arguments):
    result = call(http, name, **arguments)
    assert not result.get("isError"), result
    return result["structuredContent"]


def test_initialize_discovery_and_django_routes(http):
    result = rpc(
        http,
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "parity-tests", "version": "1"},
        },
    )["result"]
    assert result["serverInfo"]["name"] == "TastefulKit"
    tools = rpc(http, "tools/list")["result"]["tools"]
    assert {tool["name"] for tool in tools} == {
        "search_designs",
        "list_designs",
        "get_design",
        "get_design_filters",
        "get_user_info",
    }
    for tool in tools:
        assert not {"user_id", "profile_id", "api_key", "is_superuser"} & set(
            tool["inputSchema"].get("properties", {})
        )
        assert tool["description"]
    assert http.get("/").status_code == 200
    assert http.get("/api/healthcheck").json()["healthy"]
    assert http.get("/api/v1/designs").status_code == 200
    assert http.post("/mcp", follow_redirects=False).headers["location"].endswith("/mcp/")


def test_rest_mcp_list_search_detail_and_user_parity(http, client, key, design):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {key}"}
    assert data(http, "list_designs") == client.get("/api/v1/designs", **headers).json()
    with patch("apps.catalogue.services.embed", side_effect=ValueError("offline")):
        args = {"q": "warm", "tag": "minimal", "industry": "software", "kind": "landing_page"}
        assert (
            data(http, "search_designs", **args)
            == client.get("/api/v1/designs", args, **headers).json()
        )
    detail = data(http, "get_design", design_id=str(design.pk))
    assert detail == client.get(f"/api/v1/designs/{design.pk}", **headers).json()
    assert detail["screenshot_url"] and detail["thumbnail_url"]
    assert "capture_error" not in detail and "embedding" not in detail
    account = data(http, "get_user_info")
    rest_account = client.get("/api/user", **headers).json()
    # Ninja's JSON encoder rounds datetimes to milliseconds; MCP keeps microseconds.
    mcp_joined = datetime.fromisoformat(account.pop("date_joined"))
    rest_joined = datetime.fromisoformat(rest_account.pop("date_joined"))
    assert abs((mcp_joined - rest_joined).total_seconds()) < 0.001
    assert account == rest_account


@pytest.mark.parametrize("state,published", [("ready", False), ("pending", True), ("failed", True)])
def test_hidden_designs_and_filters_do_not_leak(http, design, state, published):
    design.capture_status = state
    design.published = published
    design.save()
    assert data(http, "list_designs")["items"] == []
    assert call(http, "get_design", design_id=str(design.pk))["isError"]
    filters = data(http, "get_design_filters")
    assert filters["tags"] == [] and filters["industries"] == []
    assert call(http, "get_design", design_id=str(uuid4()))["isError"]


def test_filters_and_pagination(http, user, design):
    for i in range(26):
        Design.objects.create(
            title=f"Design {i}",
            source_url="https://example.com/",
            fingerprint=f"{i:064}",
            description="Example reference",
            submitted_by=user,
            capture_status="ready",
        )
    first, second = data(http, "list_designs"), data(http, "list_designs", page=2)
    assert first["total"] == 27 and first["pages"] == 2 and len(first["items"]) == 24
    assert len(second["items"]) == 3
    assert not {d["id"] for d in first["items"]} & {d["id"] for d in second["items"]}
    filters = data(http, "get_design_filters")
    assert filters["tags"] == ["minimal"] and filters["industries"] == ["Software"]
    assert "landing_page" in {kind["value"] for kind in filters["kinds"]}


@pytest.mark.parametrize(
    "name,args",
    [
        ("get_design", {"design_id": "invalid"}),
        ("list_designs", {"page": 0}),
        ("search_designs", {"q": "a" * 301}),
        ("search_designs", {"q": ""}),
        ("submit_design_reference", {"payload": {"title": "bad"}}),
    ],
)
def test_invalid_inputs_are_tool_errors(http, name, args):
    assert call(http, name, **args)["isError"]


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer invalid"}, {"X-API-Key": "invalid"}]
)
def test_missing_invalid_keys_cannot_discover_tools(headers):
    with TestClient(application, headers={**HEADERS, **headers}) as http:
        response = http.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 401
    assert "Bearer" in response.headers["www-authenticate"]


def test_rotated_and_inactive_keys_are_rejected(http, user):
    assert data(http, "list_designs")["items"] == []
    new_key = user.profile.rotate_api_key()
    assert http.post("/mcp/", json={}).status_code == 401
    http.headers["Authorization"] = f"Bearer {new_key}"
    assert data(http, "list_designs")["items"] == []
    user.is_active = False
    user.save()
    assert http.post("/mcp/", json={}).status_code == 401


def test_host_and_origin_protection(http):
    assert http.post("/mcp/", headers={"Host": "attacker.example"}, json={}).status_code in {
        400,
        421,
    }
    assert (
        http.post("/mcp/", headers={"Origin": "https://attacker.example"}, json={}).status_code
        == 403
    )
    assert http.post("/mcp/", headers={"Origin": "http://testserver"}, json={}).status_code != 403


def test_signed_screenshot_links_are_refreshed(http, design):
    with patch.object(
        design.screenshot.storage,
        "url",
        side_effect=[
            "https://images.example/shot?signature=first",
            "https://images.example/thumb?signature=first",
            "https://images.example/shot?signature=second",
            "https://images.example/thumb?signature=second",
        ],
    ):
        first = data(http, "get_design", design_id=str(design.pk))
        second = data(http, "get_design", design_id=str(design.pk))
    assert first["screenshot_url"] != second["screenshot_url"]


def test_real_mcp_client_over_http(key, design):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(application, log_level="critical"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            url = f"http://127.0.0.1:{sock.getsockname()[1]}/mcp/"

            async def check():
                async with Client(url, auth=key) as client:
                    assert len(await client.list_tools()) == 5
                    result = await client.call_tool("get_design", {"design_id": str(design.pk)})
                    assert result.data["id"] == str(design.pk)
                    assert result.data["screenshot_url"]

            asyncio.run(check())
        finally:
            server.should_exit = True
            thread.join(timeout=5)


def test_semantic_search_matches_rest(http, client, key, design):
    with (
        patch("apps.catalogue.services.embed", return_value=[1.0] + [0.0] * 767),
        patch("apps.catalogue.services.search_vectors", return_value=[(design.pk, 0.9)]),
    ):
        result = data(http, "search_designs", q="cozy")
        rest = client.get("/api/v1/designs", {"q": "cozy"}, HTTP_X_API_KEY=key).json()
    assert result == rest
    assert result["search_mode"] == "semantic"
    assert result["items"][0]["id"] == str(design.pk)


def test_filter_discovery_is_bounded(http, design):
    tags = Tag.objects.bulk_create([Tag(name=f"style-{i:03}") for i in range(101)])
    design.tags.set(tags)
    first = data(http, "get_design_filters")
    second = data(http, "get_design_filters", page=2)
    assert len(first["tags"]) == 100 and first["tags_pages"] == 2
    assert second["tags"] == ["style-100"]


def test_user_identity_comes_from_key_not_tool_arguments(http, django_user_model, grant_membership):
    other = django_user_model.objects.create_user(username="other", email="other@example.com")
    grant_membership(other)
    http.headers["Authorization"] = f"Bearer {other.profile.rotate_api_key()}"
    assert data(http, "get_user_info")["id"] == other.pk


@pytest.mark.parametrize("admin", [False, True])
def test_mcp_is_read_only_even_for_admins(http, user, admin):
    user.is_superuser = admin
    user.save()
    assert call(http, "submit_design_reference", payload={})["isError"]
    assert call(http, "retry_design", design_id=str(uuid4()))["isError"]


def test_mcp_access_is_independent_of_subscription_status(http, user):
    from apps.billing.models import BillingAccount

    assert data(http, "list_designs")["total"] == 0
    BillingAccount.objects.update_or_create(user=user, defaults={"status": "canceled"})
    response = http.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 200
