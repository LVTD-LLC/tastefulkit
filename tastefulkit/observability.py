"""Sentry configuration and a deliberately small, content-free telemetry contract."""

import logging
import re
from contextlib import ExitStack
from urllib.parse import urlsplit, urlunsplit

import sentry_sdk
from django.conf import settings
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

SAFE_ATTRIBUTES = frozenset(
    {
        "event.name",
        "outcome",
        "error.type",
        "http.request.method",
        "http.route",
        "http.response.status_code",
        "http.response.status_class",
        "request.interface",
        "duration_ms",
        "job.success",
        "service.name",
        "sentry.environment",
        "sentry.release",
    }
)
SAFE_SPAN_DATA = frozenset({"http.request.method", "http.response.status_code", "db.system"})
EVENT_NAME = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+")


def clean_url(value):
    try:
        parsed = urlsplit(value)
        # Keep origin only: private paths can contain password reset / verification tokens.
        return urlunsplit((parsed.scheme, parsed.hostname or "", "/", "", ""))
    except (ValueError, TypeError):
        return "[Filtered]"


def scrub_event(event, hint):
    """Keep stack locations and timing, never request contents or exception values."""
    event.pop("user", None)
    event.pop("extra", None)
    event.pop("breadcrumbs", None)
    if "request" in event:
        request = event["request"]
        event["request"] = {"method": request.get("method"), "url": clean_url(request.get("url"))}
    if "logentry" in event:
        message = event["logentry"].get("message", "")
        event["logentry"] = {
            "message": message if EVENT_NAME.fullmatch(message) else "application.error"
        }
    event.pop("message", None)
    for exception in event.get("exception", {}).get("values", []):
        exception["value"] = "[Filtered: inspect stack trace]"
        for frame in exception.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)
    for span in event.get("spans", []):
        span["description"] = span.get("op", "operation")
        span["data"] = {k: v for k, v in span.get("data", {}).items() if k in SAFE_SPAN_DATA}
    trace = event.get("contexts", {}).get("trace", {})
    trace.pop("data", None)
    if event.get("transaction_info", {}).get("source") == "url":
        event["transaction"] = "unresolved"
    return event


def scrub_log(log, hint):
    if not EVENT_NAME.fullmatch(log.get("body", "")):
        return None
    log["attributes"] = {k: v for k, v in log.get("attributes", {}).items() if k in SAFE_ATTRIBUTES}
    return log


def init_sentry():
    if not settings.SENTRY_DSN:
        return
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.DEPLOYMENT_REVISION or None,
        server_name=settings.SERVICE_NAME,
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profile_session_sample_rate=settings.SENTRY_PROFILE_SESSION_SAMPLE_RATE,
        profile_lifecycle="trace",
        enable_logs=True,
        integrations=[
            DjangoIntegration(transaction_style="function_name"),
            LoggingIntegration(
                level=None, event_level=logging.ERROR, sentry_logs_level=logging.INFO
            ),
        ],
        before_send=scrub_event,
        before_send_transaction=scrub_event,
        before_send_log=scrub_log,
        before_breadcrumb=lambda breadcrumb, hint: None,
    )


def record_completion(attributes):
    """Independent of trace sampling; only bounded dimensions, no request/job IDs."""
    if not settings.SENTRY_DSN:
        return
    try:
        is_job = attributes.get("event.name") == "background_job.completed"
        prefix = "tastefulkit.job" if is_job else "tastefulkit.http"
        dimensions = {
            key: value
            for key, value in attributes.items()
            if key in {"outcome", "http.route", "http.response.status_class", "request.interface"}
        }
        sentry_sdk.metrics.count(prefix + ".completed", 1, attributes=dimensions)
        sentry_sdk.metrics.distribution(
            prefix + ".duration",
            attributes["duration_ms"],
            unit="millisecond",
            attributes=dimensions,
        )
    except Exception:
        # Observability must not alter responses or task outcomes.
        pass


def browser_context(request):
    route = getattr(getattr(request, "resolver_match", None), "view_name", "unresolved")
    public_replay = (
        not getattr(getattr(request, "user", None), "is_authenticated", False)
        and route in {"landing", "catalogue:explore", "pricing", "blog_index", "blog_post"}
        and not request.META.get("QUERY_STRING")
    )
    return {
        "sentry_config": {
            "dsn": settings.SENTRY_BROWSER_DSN,
            "environment": settings.ENVIRONMENT,
            "release": settings.DEPLOYMENT_REVISION,
            "route": route,
            "tracesSampleRate": settings.SENTRY_TRACES_SAMPLE_RATE,
            "replayEnabled": public_replay,
            "replaysSessionSampleRate": settings.SENTRY_REPLAY_SESSION_SAMPLE_RATE,
            "replaysOnErrorSampleRate": settings.SENTRY_REPLAY_ERROR_SAMPLE_RATE,
        }
        if settings.SENTRY_BROWSER_DSN
        else None,
        "sentry_trace": sentry_sdk.get_traceparent() if settings.SENTRY_DSN else "",
        "sentry_baggage": sentry_sdk.get_baggage() if settings.SENTRY_DSN else "",
    }


class SentryTaskErrorReporter:
    """Called by Django Q inside its exception handler; never includes task payloads."""

    def report(self):
        sentry_sdk.capture_exception()


def start_task_trace():
    stack = ExitStack()
    if settings.SENTRY_DSN:
        try:
            stack.enter_context(sentry_sdk.isolation_scope())
            stack.enter_context(
                sentry_sdk.start_transaction(op="queue.task", name="background_job")
            )
        except Exception:
            stack.close()
    return stack
