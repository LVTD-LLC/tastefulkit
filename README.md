# TastefulKit

A searchable library of real-world UI design examples for people and their agents.

**Live:** https://tastefulkit.com

## What's included

- Email-verified signup, login, passkeys, account settings, and personal API keys.
- Design library with text/semantic search, element/style/industry filters, and saved designs.
- One flexible model for landing pages, pricing pages, heroes, blogs, dashboards, and other UI elements.
- Admin-only, idempotent ingestion API. A background worker captures screenshots and generates embeddings.
- Private Cloudflare R2 storage with short-lived signed image URLs; Cloudflare Browser Run and Workers AI.
- Django admin for moderation and failed-capture retries.
- GitHub Actions builds one immutable GHCR image and deploys web and worker apps to CapRover.

MCP, pairwise voting, Elo rankings, and learned personal taste profiles are roadmap items, not implemented in this release. The daily research agent is external to the app: it submits through the ingestion API. No catalogue entries are hardcoded or seeded by migrations.

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

POST returns 201 (new) or 200 (existing), identified by URL + kind + selector + viewport width. Capture is asynchronous: poll `GET /api/v1/designs/{id}` for `capture_status=ready`. Admins can see pending/failed entries; other users only see published, ready designs. Retry failures with `POST /api/v1/designs/{id}/retry`. An optional CSS `selector` captures a component; `viewport_width` defaults to 1440. Screenshots belong to their original creators, not to this project.

Interactive API schema: `/api/docs`. Source URLs must resolve to public HTTP(S) addresses. Rendering takes place at Cloudflare, not inside the app's private network. Submission does not fetch an arbitrary user-supplied screenshot URL.

## Production configuration

Required environment variables:

- `ENVIRONMENT=prod`, `DEBUG=False`, `SECRET_KEY`, `SITE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`, `REDIS_URL`, `APP_PROCESS_TYPE=server|worker`
- `AWS_S3_ENDPOINT_URL`, `AWS_S3_BUCKET_NAME`, `AWS_S3_REGION_NAME=auto`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `CF_ACCOUNT_ID`, `CF_RENDER_TOKEN` with Browser Run Write and Workers AI Read
- `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL` (or SMTP settings)

Use a bucket-scoped R2 object read/write token and a separate rendering/inference token. Never use the Cloudflare administrative token in the app. R2 objects are private; signed URLs expire after 15 minutes. The capture worker stores full screenshots and thumbnail derivatives.

Search combines literal matches with cosine similarity using `@cf/baai/bge-base-en-v1.5` (768 dimensions). If embeddings are unavailable, keyword search remains functional. V1 stores vectors as JSON and scores the filtered catalogue in memory; migrate scoring to indexed pgvector before scaling to a large corpus. Metadata edits do not currently regenerate embeddings; use the submission API for ingestion and admin mainly for moderation.

### CapRover / GitHub Actions

Four isolated services: `tastefulkit`, `tastefulkit-workers`, `tastefulkit-postgres`, `tastefulkit-redis`. Postgres and Redis use CapRover-managed persistent volumes and expose no public ports. Deploy tokens are app-scoped.

Repository secrets: `CAPROVER_SERVER`, `APP_TOKEN`, `WORKERS_APP_TOKEN`. Repository variable: `WORKERS_APP_PROCESS_TYPE=worker`. A push to main builds the source SHA image in GHCR and deploys that image to both apps. The server waits for Postgres, applies migrations, and serves static assets. Worker process selection is explicit. Health endpoint: `/api/healthcheck` (database + Redis).

Back up PostgreSQL and R2 independently; persistent volumes are not backups. Schema changes need backward-compatible migrations before rollback. Redeploy a previously tested SHA image for application rollback.

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
