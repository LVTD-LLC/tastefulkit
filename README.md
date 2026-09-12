# TastefulKit

A searchable library of real-world UI design examples for people and their agents.

**Live:** https://tastefulkit.com

**User docs:** https://tastefulkit.com/docs/ — public guides for browsing, search, saved designs, accounts, and the read-only API. Development and operations guidance stays in this repository; see [maintainer notes](docs/maintainers/README.md).

## What's included

- Email-verified signup, login, passkeys, account settings, and personal API keys.
- Design library with text/semantic search, element/style/industry filters, and saved designs.
- Hosted MCP with personal API-key authentication at https://tastefulkit.com/mcp/.
- One flexible model for landing pages, pricing pages, heroes, blogs, dashboards, and other UI elements.
- Admin-only, idempotent ingestion API. A background worker captures screenshots and generates embeddings.
- Private Cloudflare R2 storage with short-lived signed image URLs; Cloudflare Browser Run and Workers AI.
- Django admin for moderation and failed-capture retries.
- GitHub Actions builds one immutable GHCR image and deploys web and worker apps to CapRover.

Pairwise voting, Elo rankings, and learned personal taste profiles are roadmap items, not implemented in this release. The daily research agent is external to the app: it submits through the ingestion API. No catalogue entries are hardcoded or seeded by migrations.

## Local development

Requires Python 3.14, uv, Node 24, and PostgreSQL (including pg_stat_statements).

```sh
cp .env.example .env
# Set DATABASE_URL, SECRET_KEY, SITE_URL=http://localhost:8000, DEBUG=True.
# Leave AWS_S3_ENDPOINT_URL empty to use local media storage.
uv sync --locked
npm ci --include=dev
npm run build
DJANGO_SETTINGS_MODULE=tastefulkit.local_settings uv run python manage.py migrate
DJANGO_SETTINGS_MODULE=tastefulkit.local_settings uv run python manage.py createsuperuser
DJANGO_SETTINGS_MODULE=tastefulkit.local_settings uv run python manage.py runserver
# In another terminal:
DJANGO_SETTINGS_MODULE=tastefulkit.local_settings uv run python manage.py qcluster
```

Local settings use the database-backed task queue and in-memory cache. Production uses Redis. Email verification is required; the local console email backend prints verification messages. To capture real pages locally, supply the Cloudflare settings below.

## Agent API

Create an API key in Account settings. Keys are shown once and stored hashed. Standard accounts can search; only active superusers can submit/retry. Provision admins explicitly with `createsuperuser`; the first signup does **not** receive admin rights.

```sh
curl 'https://tastefulkit.com/api/v1/designs?q=warm%20minimal&kind=landing_page' \
  -H "Authorization: Bearer $TASTEFULKIT_API_KEY"

curl 'https://tastefulkit.com/api/v1/designs' \
  -H "Authorization: Bearer $TASTEFULKIT_ADMIN_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"title":"Example","source_url":"https://example.com/","description":"Describe the layout, typography, palette, and useful patterns.","kind":"landing_page","tags":["minimal","editorial"],"industry":"software"}'
```

POST returns 201 (new) or 200 (existing), identified by URL + kind + selector + viewport width. Screenshot requests are paced for the Cloudflare free tier; transient provider errors retry automatically up to three times. Capture is asynchronous: poll `GET /api/v1/designs/{id}` for `capture_status=ready`. Admins can see pending/failed entries; other users only see published, ready designs. Retry failures with `POST /api/v1/designs/{id}/retry`. An optional CSS `selector` captures a component; `viewport_width` defaults to 1440. Screenshots belong to their original creators, not to this project.

Interactive API schema: `/api/docs`. Source URLs must resolve to public HTTP(S) addresses. Rendering takes place at Cloudflare, not inside the app's private network. Submission does not fetch an arbitrary user-supplied screenshot URL.

## Hosted MCP

Connect a Streamable HTTP client to `https://tastefulkit.com/mcp/` with
`Authorization: Bearer $TASTEFULKIT_API_KEY`. The key is the same personal key used
by REST; there is no separate OAuth flow. See the [connection guide](https://tastefulkit.com/docs/api-reference/mcp/)
for setup, tool arguments, and troubleshooting.

The `apps/hosted_mcp/` Django app exposes list/search/detail, filter discovery, account
info, and administrator-only submit/retry tools. Catalogue services and API-key
verification are shared with REST. Key rotation and account deactivation take
effect on the next request. Screenshot references expire after 15 minutes.

Production serves `tastefulkit.asgi:application` using Gunicorn with Uvicorn workers.
MCP is mounted at `/mcp/`; other paths still use Django and its middleware, including
WhiteNoise. Stateless HTTP with JSON responses works across workers without sticky
sessions, persistent MCP session storage, or SSE proxy buffering changes. The parent
ASGI app runs the MCP lifespan. MCP validates host and origin separately because it
does not pass through Django middleware. Only `SITE_URL` is an allowed browser origin.

For local MCP development, run the ASGI entrypoint (Django `runserver` is WSGI-only):

```sh
DJANGO_SETTINGS_MODULE=tastefulkit.local_settings uv run uvicorn tastefulkit.asgi:application --host 127.0.0.1 --port 8000
```

Use `http://localhost:8000/mcp/` locally, with a local account's API key.
The normal web and worker commands remain available. Verify MCP with
`uv run pytest apps/hosted_mcp -q`; tests include real Streamable HTTP client connectivity,
REST parity, visibility, revocation, validation, and admin boundaries.

## Production configuration

Required environment variables:

- `ENVIRONMENT=prod`, `DEBUG=False`, `SECRET_KEY`, `SITE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`, `REDIS_URL`, `APP_PROCESS_TYPE=server|worker`
- `AWS_S3_ENDPOINT_URL`, `AWS_S3_BUCKET_NAME`, `AWS_S3_REGION_NAME=auto`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `CF_ACCOUNT_ID`, `CF_RENDER_TOKEN` with Browser Run Write and Workers AI Read
- `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL` (or SMTP settings)

Use a bucket-scoped R2 object read/write token and a separate rendering/inference token. Never use the Cloudflare administrative token in the app. R2 objects are private; signed URLs expire after 15 minutes. The capture worker stores full screenshots and thumbnail derivatives.

Search combines literal matches with Qdrant cosine similarity using `@cf/baai/bge-base-en-v1.5` (768 dimensions, threshold 0.45). New vectors live only in Qdrant. PostgreSQL holds canonical metadata; legacy JSON vectors remain untouched as a migration/rollback archive and are never loaded or scored by search. Keyword search remains available if inference or Qdrant fails.

Set `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION` (default `tastefulkit-designs-bge-base-v1`), and `QDRANT_TIMEOUT_SECONDS` (default 5) on both web and worker. Leave the URL empty for local text-only development. For local semantic search, run Qdrant with a persistent `/qdrant/storage` volume and configure its HTTP endpoint and API key.

Search applies current kind, tag, case-insensitive industry, saved-user and publication/capture restrictions in PostgreSQL before Qdrant ranking. It streams eligible UUIDs in batches of 256; every batch is searched, and records are rechecked before returning results. No vector scan or corpus truncation occurs in Django. Hidden/deleted designs cannot leak through stale Qdrant points. This avoids asynchronous permission replication; for very large catalogues, profile the metadata-ID transfer before adding indexed payload filters.

Capture completion indexes the vector synchronously in the worker; failures schedule up to three independent indexing retries without recapturing screenshots. Errors remain visible in Django admin. Metadata edits do not automatically regenerate vectors; use the command below after edits. Backfill/recovery is idempotent:

```sh
python manage.py backfill_qdrant
# Recompute from current metadata, including designs already indexed (Workers AI calls):
python manage.py backfill_qdrant --regenerate
```

The default command creates/validates the collection, skips existing same-model points, imports valid legacy vectors, and regenerates missing/invalid vectors. It exits nonzero if any design fails. Neither command drops a collection or clears legacy vectors. A changed model/dimension requires a new collection and a full regeneration before switching the web app.

### Product analytics

Set `POSTHOG_API_KEY` to the project's public capture token (never a personal
management key), `POSTHOG_HOST` to its ingestion host, and optionally
`POSTHOG_BROWSER_HOST` on both web and worker apps. When configured, existing
pageview, marketing CTA, signup, login, and account-deletion events run without
an opt-in banner for anonymous and signed-in users. Old banner/SDK opt-out state
is cleared on the next page load. Without a project token, analytics remains off.
URL/property sanitization and logout identity reset remain in place; this change
does not enable session recording, click autocapture, or new product-use events.

### CapRover / GitHub Actions

Five isolated services: `tastefulkit`, `tastefulkit-workers`, `tastefulkit-postgres`, `tastefulkit-redis`, `tastefulkit-qdrant`. Postgres and Redis use CapRover-managed persistent volumes and expose no public ports. Deploy tokens are app-scoped.

Repository secrets: `CAPROVER_SERVER`, `APP_TOKEN`, `WORKERS_APP_TOKEN`. Repository variable: `WORKERS_APP_PROCESS_TYPE=worker`. A push to main builds the source SHA image in GHCR and deploys that image to both apps. The server waits for Postgres, applies migrations, and serves static assets. Worker process selection is explicit. Health endpoint: `/api/healthcheck` (database + Redis + configured Qdrant collection). Qdrant failures return 503 even though user searches degrade to keywords.

Qdrant follows Citeguild's private CapRover layout: `notExposeAsWebApp=true`, no published ports, one replica pinned to its persistent-volume node, `/qdrant/storage` mounted from `tastefulkit-qdrant-data`, API-key authentication, telemetry disabled. App URL: `http://srv-captain--tastefulkit-qdrant:6333`. The server API key is a dedicated project credential, not Citeguild's key, and is stored in Infisical as `TASTEFULKIT_QDRANT_API_KEY`. The initial tested image is `qdrant/qdrant@sha256:0bd98fa7977f1e75694779359ca4e212822e5a71334e28421182f72f209d5286`.

Rollout: provision Qdrant, configure both apps, create/backfill the collection, then deploy the code and run the backfill again to cover submissions during rollout. Verify all ready designs are indexed and health is green. Application rollback uses the previous immutable image and does not delete Qdrant or PostgreSQL data. Old code cannot semantically search new Qdrant-only vectors; regenerate/export those before relying on old-code semantic search.

Back up PostgreSQL, R2, and Qdrant snapshots independently; persistent volumes are not backups. Schema changes need backward-compatible migrations before rollback. Redeploy a previously tested SHA image for application rollback.

## Verification

```sh
uv run pytest
uv run ruff check .
npm run lint
npm run build
uv run python manage.py makemigrations --check --dry-run
```

## Generation provenance

Generated from the official [djass / Django SaaS Starter](https://github.com/rasulkireev/django-saas-starter) Cookiecutter template at `a81c92f096fe79a15158c8e5df49f1437d68c515`, using the same template as the hosted generator. The hosted djass API credential was not available, so generation ran directly from the official template. Enabled: S3, PostHog wiring, CI, health checks, docs. Disabled: Stripe, blog, MJML, MCP, Sentry, starter AI. The catalogue implements its own screenshot/embedding integration.
