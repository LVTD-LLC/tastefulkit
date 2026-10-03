from unittest.mock import Mock, patch

import pytest
import requests
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django_q.models import Schedule

from apps.core.traffic import CACHE_KEY, refresh_pageviews, traffic_context


@pytest.fixture(autouse=True)
def traffic_cache():
    cache.delete(CACHE_KEY)
    yield
    cache.delete(CACHE_KEY)


@override_settings(POSTHOG_PERSONAL_API_KEY="server-only", POSTHOG_PROJECT_ID="12345")
def test_refresh_counts_only_production_pageviews_and_caches_zero():
    with patch("apps.core.traffic.requests.post") as post:
        post.return_value = Mock(json=lambda: {"results": [[0]]})
        assert refresh_pageviews() is True
    assert traffic_context(None) == {"navbar_pageviews": 0}
    args = post.call_args.kwargs
    query = args["json"]["query"]["query"]
    assert "event = '$pageview'" in query
    assert "INTERVAL 24 HOUR" in query
    assert "tastefulkit.com" in query
    assert args["headers"]["Authorization"] == "Bearer server-only"
    assert args["timeout"] == (3, 15)


@pytest.mark.parametrize(
    "payload",
    [{}, {"results": []}, {"results": [[-1]]}, {"results": [[True]]}, {"results": [["bad"]]}],
)
@override_settings(POSTHOG_PERSONAL_API_KEY="server-only", POSTHOG_PROJECT_ID="12345")
def test_invalid_results_do_not_replace_cache(payload):
    cache.set(CACHE_KEY, 19, 900)
    with patch("apps.core.traffic.requests.post") as post:
        post.return_value = Mock(json=lambda: payload)
        assert refresh_pageviews() is False
    assert traffic_context(None)["navbar_pageviews"] == 19


@override_settings(POSTHOG_PERSONAL_API_KEY="server-only", POSTHOG_PROJECT_ID="12345")
def test_outage_is_not_zero_and_does_not_break_pages():
    with patch("apps.core.traffic.requests.post", side_effect=requests.Timeout):
        assert refresh_pageviews() is False
    assert traffic_context(None)["navbar_pageviews"] is None
    with patch("apps.core.traffic.cache.get", side_effect=ConnectionError):
        assert traffic_context(None)["navbar_pageviews"] is None


@override_settings(POSTHOG_PERSONAL_API_KEY="")
def test_unconfigured_does_not_query():
    with patch("apps.core.traffic.requests.post") as post:
        assert refresh_pageviews() is False
    post.assert_not_called()


@pytest.mark.django_db
def test_schedule_is_idempotent():
    call_command("refresh_pageviews", "--schedule")
    call_command("refresh_pageviews", "--schedule")
    schedule = Schedule.objects.get(name="navbar-pageviews")
    assert schedule.minutes == 5


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/", "/explore/", "/how-to-use/"])
def test_navbar_traffic(client, url):
    cache.set(CACHE_KEY, 1234, 900)
    response = client.get(url)
    assert response.status_code == 200
    html = response.content.decode()
    assert "1,234 views in the last 24 hours" in html
    assert "server-only" not in html
    cache.set(CACHE_KEY, 0, 900)
    assert "0 views in the last 24 hours" in client.get(url).content.decode()
    cache.delete(CACHE_KEY)
    assert "views in the last 24 hours" not in client.get(url).content.decode()


def test_failed_refresh_does_not_extend_freshness():
    with (
        patch("apps.core.traffic.cache.set") as write,
        override_settings(POSTHOG_PERSONAL_API_KEY="server-only", POSTHOG_PROJECT_ID="12345"),
        patch("apps.core.traffic.requests.post", side_effect=requests.Timeout),
    ):
        assert refresh_pageviews() is False
    write.assert_not_called()


@override_settings(POSTHOG_PERSONAL_API_KEY="server-only", POSTHOG_PROJECT_ID="12345")
def test_success_expires_after_fifteen_minutes():
    with (
        patch("apps.core.traffic.requests.post") as post,
        patch("apps.core.traffic.cache.set") as write,
    ):
        post.return_value = Mock(json=lambda: {"results": [[42]]})
        assert refresh_pageviews() is True
    write.assert_called_once_with(CACHE_KEY, 42, timeout=900)
