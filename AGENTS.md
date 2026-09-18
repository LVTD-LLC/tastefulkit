# AGENTS.md - TastefulKit

TastefulKit is a searchable library of real website design references, built
with Django. Keep changes small, tested, and aligned with the existing app
structure. This file holds implementation and operations guidance;
[README.md](README.md) is for product users and [CONTRIBUTING.md](CONTRIBUTING.md)
is the contribution and merge contract.

## Agent Contract

- Treat this file as the canonical guidance for coding agents in this project.
- Keep guidance tool-neutral. Do not add IDE-specific, vendor-specific, or
  single-agent instruction files. Repo-scoped Agent Skills may live under
  `.agents/skills/` when they describe portable workflows.
- Add nested `AGENTS.md` files only when a subdirectory needs scoped guidance.
- Keep personal preferences and machine-local paths out of committed
  instructions.
- Store secrets in environment variables or `.env`; never print, log, hard-code,
  or commit API keys.
- Treat log fields as a public monitoring contract: use stable dotted
  `event.name` values, scalar `extra` fields, binary `success`/`failure`
  outcomes, and never include credentials, bodies, email addresses, arbitrary
  metadata, task arguments/results, or user-owned content.

## Project Map

- `apps/core/` - shared domain logic, auth-adjacent flows, profiles, forms,
  utilities, background tasks, and common tests.
- `apps/pages/` - landing, pricing, legal, and other static or marketing pages,
  plus repository-tracked content such as blog and docs when generated.
- `apps/api/` - Django Ninja API schemas, auth, services, and routers.
- `apps/hosted_mcp/` - authenticated hosted MCP tools; mounted by `tastefulkit/asgi.py`.
- `apps/pages/content/docs/` - public user-facing Markdown documentation content.
- `tastefulkit/settings.py` - environment-driven Django
  settings.
- `tastefulkit/test_settings.py` - pytest-only settings
  that keep cache, media, email, and Django Q2 state local to test runs.
- `tastefulkit/urls.py` - top-level URL routing.
- `conftest.py` - shared pytest fixtures, including the guarded pgsandbox
  database settings hook used by `make test-local-postgres` so pytest-django
  reuses an existing PGSandbox database with `--reuse-db`.
- `frontend/templates/` - Django templates.
- `frontend/src/js/` - small browser modules copied to `frontend/static/js/`.
- `frontend/src/styles/` - Tailwind CSS and global styles.
- `frontend/static/` - Django-served static asset output.
- `docs/quality.md` - local CI path and touched-area quality command matrix.
- `docs/code-tours/` - concise flow tours for common generated-project
  architecture and verification paths.
- `docs/agent-task-templates.md` - task-framing templates for common Django,
  API, frontend, background job, dependency, and agent-guidance changes.
- `docs/agent-evals/seed-tasks.md` - seed tasks for repeatable agent evaluation
  and regression mining.
- `DESIGN.md` - design-system source of truth for humans and AI tools.
- `.agents/skills/` - bundled cross-agent skills for project-specific workflows.

## Workflow

1. Read `CONTRIBUTING.md`, `DESIGN.md`, `docs/quality.md`, and the files around the
   requested change.
2. Branch from the latest `main` before implementation; ship through a pull
   request, never a direct commit to `main`.
3. Put code in the smallest appropriate app or frontend module.
4. Add or update tests for feature work, bug fixes, and risky refactors.
5. Use `docs/quality.md` to run targeted checks first, then broader checks
   before finishing.
6. Update `CHANGELOG.md` under the current ISO date heading (`## YYYY-MM-DD`)
   for user-visible behavior changes.
7. Before merging, require a completed ReviewGate **5/5** result and successful
   `ReviewGate` check for the exact current PR head, passing CI, and addressed
   material review feedback. A timeout, skipped review, stale result, or green
   workflow without a passing review is not approval. See `CONTRIBUTING.md`.

## Repo-Scoped Skills

- `.agents/skills/caprover-deployment/SKILL.md` - portable CapRover deployment
  workflow for coding agents that support the Agent Skills convention, and
  readable fallback instructions for agents that do not.
- `.agents/skills/local-terminal-development/SKILL.md` - local agent
  development workflow for running Django, Django Q2, tests, and frontend
  assets from terminal commands, optionally backed by Compose services.
- `.agents/skills/alpinejs-django/SKILL.md` - Alpine.js patterns for
  Django-rendered templates, including coordination with HTMX partial updates.
- `.agents/skills/django-ninja/SKILL.md` - Django Ninja endpoint, schema,
  router, authentication, OpenAPI, and API test guidance.
- `.agents/skills/django-q2/SKILL.md` - Django Q2 background task, schedule,
  worker, Redis broker, and ORM broker guidance.
- `.agents/skills/django-htmx/SKILL.md` - portable Django/HTMX patterns for
  server-rendered partial updates, forms, swaps, events, and Alpine.js
  coordination.
- `.agents/skills/pgsandbox-testing/SKILL.md` - disposable local Postgres
  testing with PGSandbox MCP and this project's `DATABASE_URL` test target.
- `.agents/skills/frontend-ui-quality/SKILL.md` - portable UI quality workflow
  for Django templates, Tailwind CSS, responsive behavior, accessibility,
  motion, and generated-project design-system alignment.
- `.agents/skills/agent-reliability/SKILL.md` - reliability workflow for
  agent-driven changes, including task framing, high-risk behavior kernels,
  parity tests, coverage visibility, type-check rollout, and eval seeds.
- `.agents/skills/property-based-testing/SKILL.md` - Hypothesis workflow for
  invariants, round trips, parsers, state transitions, and Django database
  properties.

## Application contracts

- The catalogue uses one design model for landing pages, pricing pages, heroes,
  blogs, dashboards, and other UI elements. External agents prepare metadata, screenshots,
  thumbnails, DESIGN.md and embeddings; the admin-only multipart POST validates, stores
  and indexes them synchronously. Django admin handles visibility, not content creation.
- Signup requires email verification. Account settings support passkeys and
  personal API keys. Only explicitly provisioned active superusers may ingest
  complete prepared designs; never grant admin rights to the first signup.
- The authenticated arena compares published ready references within the same kind
  and viewport family (<768px mobile, otherwise desktop). Signed one-hour pair
  tokens bind user and taste generation; POSTs enforce CSRF, current visibility,
  pair compatibility, one vote per pair/generation and 30 actions/minute/account.
- ArenaState serializes ballots and global Elo writes in one transaction. First
  votes per account/pair count globally (initial 1000, K=32); resetting personal
  taste never duplicates global weight. UUID snapshots retain exact replay after
  design deletion; account deletion unlinks ballots. Rebuild under the same lock
  with `python manage.py rebuild_arena_ratings` (not a scheduled operation).
- Personal rankings replay current-generation choices, then add normalized metadata
  affinity from tags/kinds/industries and saves. They use no catalogue inference,
  query embeddings, or other accounts' taste. No personal signal falls back to
  global Elo. Reset starts a new generation and excludes older saves without
  removing the collection. Rankings and profile operations remain session-only;
  REST/MCP catalogue contracts are unchanged.
- The daily research agent is external and submits via the ingestion API.
  No catalogue entries are hardcoded or seeded by migrations.

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

Local settings use the database-backed task queue and in-memory cache. Production uses Redis. Email verification is required. With Mailgun/SMTP unset, the console email backend prints verification messages; do not use production email credentials for local development. Prepare assets outside the app; Cloudflare is used only for query embeddings.

## Agent API

Create an API key in Account settings. Keys are shown once and stored hashed.
Only active superusers may submit; staff status and the first signup confer no
write access. All catalogue creation/refreshes use `POST /api/v1/designs` as multipart:
JSON `payload`, binary `screenshot`, `thumbnail`, and UTF-8 `design_md`.
See [the submission contract](apps/pages/content/docs/api-reference/design-library.md)
for exact preparation requirements, limits, a curl example and the pinned DESIGN.md format.

The payload supplies a timestamp and a finite nonzero 768-value embedding from
`@cf/baai/bge-base-en-v1.5`. No source fetching, rendering, resizing, content generation,
example embedding inference or asynchronous processing occurs in the app. Images are
validated but stored byte-for-byte. DESIGN.md is stored durably in PostgreSQL, escaped
in the detail page, available as a protected download and included in REST/MCP detail.

New submissions return 201 ready/published. Same URL + kind + selector + viewport width
returns 200 unchanged; `replace_existing: true` replaces the full bundle while preserving
ID, saves, submitter and moderation visibility. Files use unique names; DB changes are
transactional and old files are cleaned after commit. Qdrant uses synchronous writes
and best-effort compensation on errors (cross-service transactions are not available).
Storage/index failure returns 503; failed compensations log stable events for recovery.
No secrets or user content are logged. Retry the complete bundle externally.

The old retry endpoint and MCP writes are removed. Legacy task import paths are inert
compatibility sinks so already-queued capture/index jobs cannot generate content after
rollout. Legacy entries stay visible; agents backfill them through explicit replacement
POSTs. Do not hide or delete the catalogue as a migration shortcut.

Interactive API schema: `/api/docs`. Search/read permissions and signed asset URLs remain
unchanged. No externally supplied asset URL is fetched by the app.

## Hosted MCP

Connect a Streamable HTTP client to `https://tastefulkit.com/mcp/` with
`Authorization: Bearer $TASTEFULKIT_API_KEY`. The key is the same personal key used
by REST; there is no separate OAuth flow. See the [connection guide](https://tastefulkit.com/docs/api-reference/mcp/)
for setup, tool arguments, and troubleshooting.

The `apps/hosted_mcp/` Django app exposes list/search/detail, filter discovery, account
info tools, all read-only. Catalogue services and API-key
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
- `CF_ACCOUNT_ID`, `CF_RENDER_TOKEN` with Workers AI Read for search query embeddings only
- `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN`, `DEFAULT_FROM_EMAIL` (or SMTP settings)

Use a bucket-scoped R2 object read/write token and a separate query-inference token. Never use the Cloudflare administrative token in the app. R2 objects are private; signed URLs expire after 15 minutes. External agents supply both full screenshots and prepared thumbnails.

Search combines literal matches with Qdrant cosine similarity using `@cf/baai/bge-base-en-v1.5` (768 dimensions, threshold 0.45). New vectors live only in Qdrant. PostgreSQL holds canonical metadata; legacy JSON vectors remain untouched as a migration/rollback archive and are never loaded or scored by search. Keyword search remains available if inference or Qdrant fails.

Set `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION` (default `tastefulkit-designs-bge-base-v1`), and `QDRANT_TIMEOUT_SECONDS` (default 5) on both web and worker. Leave the URL empty for local text-only development. For local semantic search, run Qdrant with a persistent `/qdrant/storage` volume and configure its HTTP endpoint and API key.

Search applies current kind, tag, case-insensitive industry, saved-user and publication/capture restrictions in PostgreSQL before Qdrant ranking. It streams eligible UUIDs in batches of 256; every batch is searched, and records are rechecked before returning results. No vector scan or corpus truncation occurs in Django. Hidden/deleted designs cannot leak through stale Qdrant points. This avoids asynchronous permission replication; for very large catalogues, profile the metadata-ID transfer before adding indexed payload filters.

Submission indexes the supplied vector synchronously before returning success; there
are no automatic indexing retries. Search query embedding generation stays separate.
The `backfill_qdrant` command imports valid existing legacy vectors and skips indexed
records; it never regenerates missing vectors. Agents must resubmit complete bundles
for missing vectors or metadata refreshes. `--regenerate` is retired. A changed model
requires a new collection and externally prepared compatible vectors before switching.

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

Qdrant uses a private CapRover layout: `notExposeAsWebApp=true`, no published ports, one replica pinned to its persistent-volume node, `/qdrant/storage` mounted from `tastefulkit-qdrant-data`, API-key authentication, telemetry disabled. App URL: `http://srv-captain--tastefulkit-qdrant:6333`. The server API key is a dedicated project credential, not a shared cross-project key, and is stored in Infisical as `TASTEFULKIT_QDRANT_API_KEY`. The initial tested image is `qdrant/qdrant@sha256:0bd98fa7977f1e75694779359ca4e212822e5a71334e28421182f72f209d5286`.

Rollout: provision Qdrant, configure both apps, create/backfill the collection, then deploy the code and run the backfill again to cover submissions during rollout. Verify all ready designs are indexed and health is green. Application rollback uses the previous immutable image and does not delete Qdrant or PostgreSQL data. Old code cannot semantically search new Qdrant-only vectors; regenerate/export those before relying on old-code semantic search.

Back up PostgreSQL, R2, and Qdrant snapshots independently; persistent volumes are not backups. Schema changes need backward-compatible migrations before rollback. Redeploy a previously tested SHA image for application rollback.

## Generation provenance

Generated from the official [djass / Django SaaS Starter](https://github.com/rasulkireev/django-saas-starter)
Cookiecutter template at `a81c92f096fe79a15158c8e5df49f1437d68c515`.
The initial template enabled S3, PostHog wiring, CI, health checks, and docs;
it disabled Stripe, blog, MJML, MCP, Sentry, and starter AI. These are historical
generation choices, not the current feature list: TastefulKit subsequently added
its own screenshot/embedding integration and authenticated hosted MCP.

## Commands

Agent local development with Compose-backed services:

```bash
cp .env.agent.example .env
make agent-services
make terminal-setup
uv run python manage.py makemigrations
make terminal-migrate
make terminal-manage check
make terminal-web
```

Terminal local development without Docker:

```bash
cp .env.terminal.example .env
make terminal-setup
uv run python manage.py makemigrations
make terminal-migrate
make terminal-manage check
make terminal-web
```

Run these in separate terminals when the web app needs background jobs and live
frontend assets:

```bash
make terminal-worker
make terminal-assets
```

Local Docker-backed development:

```bash
make serve
make manage check
make test
```

When running multiple generated projects or same-slug clones on one machine,
override local ports and, for same directory names, `COMPOSE_PROJECT_NAME`:

```bash
LOCAL_WEB_PORT=8001 LOCAL_POSTGRES_PORT=55433 LOCAL_REDIS_PORT=56380 make agent-services
DJANGO_RUNSERVER_PORT=8001 SITE_URL=http://localhost:8001 POSTGRES_PORT=55433 REDIS_PORT=56380 make terminal-web
COMPOSE_PROJECT_NAME=tastefulkit-agent-a LOCAL_WEB_PORT=8002 LOCAL_POSTGRES_PORT=55434 LOCAL_REDIS_PORT=56381 LOCAL_MAILHOG_SMTP_PORT=11025 LOCAL_MAILHOG_UI_PORT=18025 make serve
```

Quality checks:

```bash
make ci-local
make python-quality
make frontend-check
make migrations-check
make django-check
make coverage-high-risk -- -q
make mutation-high-risk -- 'apps.core.utils.*'
```

Targeted tests:

```bash
make test apps/core/tests/test_example.py
make test apps/core/tests/test_example.py::test_specific_case
make test -- -k keyword -q
make terminal-test apps/core/tests/test_example.py
make terminal-test apps/core/tests/test_example.py::test_specific_case
make terminal-test -- -k keyword -q
```

Disposable local Postgres tests:

```bash
DATABASE_URL="<pgsandbox connection string>" make test-local-postgres
DATABASE_URL="<pgsandbox connection string>" make test-local-postgres -- -k keyword -q
```

Host-level checks used by CI:

```bash
make python-quality
make frontend-check
make migrations-check
make django-check
make coverage-high-risk COVERAGE_FAIL_UNDER=0 -- -q
```

Mutation testing is an opt-in strength check, not part of the default local or
per-commit CI path. Run it after focused pytest checks for high-risk behavior
kernels, then inspect survivors with `make mutation-results`.

Frontend:

```bash
npm ci
npm run build
npm run lint
```

## Implementation Rules

- Use Django conventions and the existing app boundaries before creating new
  abstractions.
- Keep business logic out of templates; use views, forms, services, model
  methods, or template tags as appropriate.
- Change models first, then generate migrations with `make makemigrations`
  inside Docker or `make terminal-makemigrations` without Docker. Inspect
  generated migrations before committing them.
- Do not hand-edit historical migrations unless explicitly required.
- Keep auth flows compatible with `django-allauth`, including email, passkey,
  MFA, signup gating, and password reset flows.
- Keep light and dark mode readable when changing templates.
- Use HTMX for server-rendered partial updates and Alpine.js for local browser
  state. Keep plain browser modules in `frontend/src/js/` for shared DOM
  behavior.
- Read `.agents/skills/frontend-ui-quality/SKILL.md` before changing Django
  templates, Tailwind CSS, layout, responsive behavior, motion, frontend copy,
  or UI component states.
- Read `.agents/skills/agent-reliability/SKILL.md` before broad agent-driven
  changes, CI/quality workflow updates, test architecture changes, multi-surface
  behavior changes, or agent-evaluation work.
- Use `docs/agent-task-templates.md` to frame repeatable tasks and
  `docs/code-tours/README.md` to orient before changing established flows.
- Use `docs/agent-evals/seed-tasks.md` when evaluating agents or mining
  repeated agent failures back into tests, docs, or workflow guardrails.
- Read `.agents/skills/alpinejs-django/SKILL.md` before adding or changing
  Alpine.js behavior in Django templates.
- Read `.agents/skills/django-htmx/SKILL.md` before adding or changing HTMX
  interactions.
- Keep styles aligned with `DESIGN.md` and Tailwind conventions.
- For CapRover deploys or deploy fixes, read `.agents/skills/caprover-deployment/SKILL.md` first.
- Before running the generated app locally for agent work, read
  `.agents/skills/local-terminal-development/SKILL.md` first.
- For pre-PR verification and touched-area command choices, use
  `docs/quality.md`.
- For Django Ninja API endpoints, schemas, routers, authentication, OpenAPI
  docs, or API tests, read `.agents/skills/django-ninja/SKILL.md` first.
- For Django Q2 background tasks, scheduled jobs, worker changes, or broker
  changes, read `.agents/skills/django-q2/SKILL.md` first.
- For disposable local Postgres testing through MCP, read
  `.agents/skills/pgsandbox-testing/SKILL.md` first. Create the sandbox with the
  MCP tool, run checks with `DATABASE_URL`, then delete the sandbox.
- For test-suite speed, profiling, CI split changes, parallel execution,
  fixture/data refactors, or test mocks, read the matching Django test skill
  under `.agents/skills/` before changing code or workflow files.
- For invariants, round trips, parsers, normalizers, state transitions, or broad
  input spaces, read `.agents/skills/property-based-testing/SKILL.md` before
  adding Hypothesis tests.

## Agent Guidance

- This file ships regardless of optional product features. Optional focused
  skills under `.agents/skills/` may be removed when their corresponding
  runtime feature is disabled.
- Keep this file concise enough for agents to read before every task.
- Prefer exact commands and file paths over generic "follow best practices"
  instructions.
- Update this file when project structure, test commands, security constraints,
  or major workflows change.
- Content-specific writing guidance lives in `apps/pages/content/AGENTS.md`.
