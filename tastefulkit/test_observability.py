from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, override_settings

from tastefulkit.observability import browser_context, record_completion, scrub_event, scrub_log


def test_scrubbing_removes_secrets_from_all_event_surfaces():
    event = {
        "user": {"email": "secret@example.com"},
        "extra": {"api_key": "secret"},
        "request": {
            "url": "https://user:secret@tastefulkit.com/reset/secret/?key=secret",
            "data": "secret",
            "headers": {"Authorization": "secret"},
        },
        "breadcrumbs": [{"message": "secret"}],
        "exception": {
            "values": [
                {
                    "value": "secret",
                    "type": "ValueError",
                    "stacktrace": {"frames": [{"filename": "app.py", "vars": {"key": "secret"}}]},
                }
            ]
        },
        "spans": [{"op": "db", "description": "SELECT secret", "data": {"db.statement": "secret"}}],
        "contexts": {"trace": {"trace_id": "abc", "data": {"secret": "secret"}}},
        "transaction": "/reset/secret/",
        "transaction_info": {"source": "url"},
    }
    cleaned = scrub_event(event, {})
    assert "secret" not in repr(cleaned)
    assert cleaned["exception"]["values"][0]["stacktrace"]["frames"][0]["filename"] == "app.py"
    assert cleaned["contexts"]["trace"]["trace_id"] == "abc"


def test_logs_drop_free_text_and_noncontract_attributes():
    assert scrub_log({"body": "password=secret"}, {}) is None
    log = scrub_log(
        {
            "body": "http.request.completed",
            "attributes": {"http.route": "landing", "user_id": 1, "email": "secret"},
        },
        {},
    )
    assert log["attributes"] == {"http.route": "landing"}


@override_settings(SENTRY_DSN="enabled")
def test_metrics_have_bounded_dimensions_and_fail_open():
    with (
        patch("sentry_sdk.metrics.count") as count,
        patch("sentry_sdk.metrics.distribution") as duration,
    ):
        record_completion(
            {
                "event.name": "http.request.completed",
                "duration_ms": 12,
                "http.route": "landing",
                "user_id": 1,
                "request.id": "arbitrary",
            }
        )
        assert count.call_args.kwargs["attributes"] == {"http.route": "landing"}
        assert duration.call_args.args == ("tastefulkit.http.duration", 12)
        count.side_effect = RuntimeError("offline")
        record_completion({"duration_ms": 1})


@override_settings(SENTRY_BROWSER_DSN="https://public@example.com/1")
def test_replay_only_on_anonymous_public_pages_without_query():
    request = RequestFactory().get("/")
    request.resolver_match = SimpleNamespace(view_name="landing")
    request.user = SimpleNamespace(is_authenticated=False)
    assert browser_context(request)["sentry_config"]["replayEnabled"]
    request.user.is_authenticated = True
    assert not browser_context(request)["sentry_config"]["replayEnabled"]
    request.user.is_authenticated = False
    request.resolver_match.view_name = "account_login"
    assert not browser_context(request)["sentry_config"]["replayEnabled"]
    request.resolver_match.view_name = "landing"
    request.META["QUERY_STRING"] = "token=private"
    assert not browser_context(request)["sentry_config"]["replayEnabled"]


@override_settings(SENTRY_DSN="https://public@example.com/1", SENTRY_TRACES_SAMPLE_RATE=1.0)
def test_real_sdk_emits_scrubbed_errors_traces_logs_and_metrics():
    import logging

    import sentry_sdk
    from sentry_sdk.transport import Transport

    from tastefulkit.observability import SentryTaskErrorReporter, init_sentry, start_task_trace

    envelopes = []

    class CollectTransport(Transport):
        def capture_envelope(self, envelope):
            envelopes.append(envelope)

    original_init = sentry_sdk.init
    previous_client = sentry_sdk.get_client()

    def collect_init(**options):
        return original_init(**options, transport=CollectTransport)

    try:
        with patch("sentry_sdk.init", side_effect=collect_init):
            init_sentry()
        with start_task_trace():
            try:
                raise ValueError("private-api-key-must-not-leak")
            except ValueError:
                SentryTaskErrorReporter().report()
            logging.getLogger("tastefulkit.monitoring").info("monitoring.smoke.completed")
            record_completion(
                {"event.name": "background_job.completed", "duration_ms": 123, "outcome": "success"}
            )
        sentry_sdk.flush(timeout=5)
        types = {item.type for envelope in envelopes for item in envelope.items}
        assert {"event", "transaction", "log", "trace_metric"} <= types
        events = [
            item.payload.json
            for envelope in envelopes
            for item in envelope.items
            if item.type == "event"
        ]
        assert events and "private-api-key-must-not-leak" not in repr(
            events[0].get("exception", {}).get("values", [{}])[0].get("value")
        )
        assert events[0]["exception"]["values"][0]["type"] == "ValueError"
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.get_global_scope().set_client(previous_client)
