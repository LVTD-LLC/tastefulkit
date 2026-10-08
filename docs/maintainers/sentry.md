# Sentry operations

Project: https://sentry.io/organizations/rasulkireev/projects/tastefulkit/

Set `SENTRY_DSN` and `SENTRY_BROWSER_DSN` on web and worker (same image).
No Sentry management/auth token belongs in the application. The browser DSN is
public by design. Empty DSNs disable telemetry for local/test runs.
Release is the immutable `DEPLOYMENT_REVISION`; environment is `ENVIRONMENT`.

## Coverage and sampling

- Errors: Django/ASGI, browser and Django Q2's error-reporter hook. Error event
  sampling is 100%, subject to Sentry filtering/quotas. Exception values, locals,
  request headers/bodies/cookies, user fields and breadcrumbs are removed.
  Stack locations are retained; diagnose using source and operational event names.
- Tracing: SDK Django/ASGI/database/outbound spans and browser navigation/fetch/XHR;
  queue execution has a separate isolated `background_job` root (not propagated
  from the enqueue request). Default trace sample rate 0.2 on web and browser.
  SQL/HTTP span descriptions/data are removed to prevent content leakage.
- Python profiling: continuous trace lifecycle, not deprecated transaction-based
  profiles. Profile-session sampling 1.0 means each process is eligible; recording
  runs only during sampled traces. No browser CPU profiler is enabled.
- Logs: canonical dotted application event names only, with an attribute allowlist.
  Console/vendor free text and arbitrary extra fields are dropped. Existing PostHog
  logging is unchanged. Browser emits `browser.monitoring.started` only.
- Metrics: `tastefulkit.http.completed`/`.duration` and
  `tastefulkit.job.completed`/`.duration` (milliseconds). Route names, interface,
  status class and outcome only; no user/query/request/job IDs. Health checks are
  omitted. Browser emits `tastefulkit.browser.page_loaded` with route name.
- Replay: 10% sessions / 100% on error on explicitly allowed anonymous public
  pages only. Text/inputs masked, media/scripts blocked, console/network events
  dropped, request/response bodies disabled. No signed-in/account replay, nor
  URLs with query strings/fragments. Other public pages remain excluded until
  reviewed. A sampling decision is not proof of ingestion or playback.

All rates can be adjusted through the variables in `.env.example`. Provider plan,
quotas and ingestion limits still apply; no billing plan was upgraded.

The browser SDK is pinned, self-hosted and bundled without minification. Stack
locations are directly readable; no source-map upload token or private source
archive is published. `npm run build` and the watch pipeline both build it.

## Verification and rollback

Run `pytest tastefulkit/test_observability.py`, `npm run test:analytics`,
`npm run lint`, `npm run build`, and the full CI suite. Verify actual envelopes
and Sentry readback for errors, transactions, logs, metrics, profiles and replay.
Use a controlled operator browser/session and a labelled synthetic exception;
do not add public crash routes. Test worker exception reporting without touching
customer jobs. Recheck `/api/healthcheck` and running web/worker revision.

For incident rollback clear both DSNs on both services and redeploy/restart,
or deploy the prior immutable image. No schema migrations are introduced.

SDK references: [Django](https://docs.sentry.io/platforms/python/integrations/django/),
[metrics](https://docs.sentry.io/platforms/python/metrics/),
[profiles](https://docs.sentry.io/platforms/python/profiling/),
[replay controls](https://docs.sentry.io/platforms/javascript/session-replay/configuration/).
