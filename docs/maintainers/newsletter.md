# TastefulKit newsletter

The homepage and public design/UI-library detail pages share an optional weekly
newsletter form. `apps/pages/newsletter.py` validates email and CSRF, applies a
honeypot and shared-cache rate limit (10 attempts per IP per hour), then calls
Listmonk's public subscription API for the configured double-opt-in list only.
Listmonk owns confirmation and unsubscribe state; Django never creates an account,
stores the submitted address, or preconfirms a subscriber. Duplicate requests use
one generic response. Provider failures retain a recoverable form with HTTP 503.
The limiter fails closed if cache access fails. Redis is required in production;
cache flushes reset the abuse budget. `X-Real-IP` is trusted only when explicitly
configured behind CapRover, whose proxy overwrites it. Never expose the app port.

## Configuration

- `NEWSLETTER_LISTMONK_URL=http://tastefulkit-listmonk:9000`
- `NEWSLETTER_LIST_UUID`: UUID of **Weekly TastefulKit inspiration**, list 3.
- `NEWSLETTER_TRUST_PROXY=True` behind CapRover; false by default.

Set these on web/workers. No Listmonk admin credential belongs in Django.
Empty URL/UUID hides the form and disables requests. No migrations are needed.
The signup/error pages are uncached; addresses are not placed in redirect URLs,
analytics events, logs, or negotiated Markdown. The form works without JavaScript.

## Operations

- Admin: https://newsletter.tastefulkit.com/admin/
- Host: main CapRover at `138.201.126.181`.
- Apps: `tastefulkit-listmonk`, `tastefulkit-listmonk-db`.
- Listmonk pinned to 6.2.0, upstream digest
  `sha256:f535d59e14991337a9f2d570273685378ae86b0d7698c3e00da444e3bc205286`.
- PostgreSQL 17; persistent database volume and `/listmonk/uploads` volume.
- Dedicated private overlay for the database; Listmonk also joins the shared
  proxy network with DNS-round-robin endpoints to avoid allocating a VIP there.
  Preserve the CapRover service override across deployments.
- Credentials in Infisical Openclaw / prod / `/projects/tastefulkit`:
  `LISTMONK_ADMIN_USER`, `LISTMONK_ADMIN_PASSWORD`, `LISTMONK_DB_PASSWORD`,
  `LISTMONK_SMTP_PASSWORD`. Never print or commit them.
- Mailgun `mg.tastefulkit.com`; separate SMTP account
  `newsletter@mg.tastefulkit.com`, `smtp.mailgun.org:587`, verified STARTTLS.
  Sender: **Rasul at TastefulKit <rasul@tastefulkit.com>**.
  Existing transactional credentials and receiving DNS remain unchanged.
- Listmonk open/click tracking disabled. Preserve Mailgun bounce/complaint
  suppressions; provider suppression is authoritative. This integration does not
  mirror Mailgun events back into Listmonk.
- Custom proxy configuration blocks `/api/public/subscription` externally and
  redirects public signup forms to the app. Confirmation/preferences/unsubscribe
  links remain public. Preserve these rules when changing Nginx configuration.

No campaign, automatic send schedule, or receiving inbox is created. Draft the
first edition in Listmonk; check sender, list, and unsubscribe footer before sending.

## Verification and rollback

Run `uv run pytest apps/pages/test_newsletter.py -q` against PostgreSQL. Verify
mobile/desktop and both themes, invalid email, provider failure, confirmation and
unsubscribe using an operator-owned inbox. Do not test sends with customer emails.

Before upgrading Listmonk, make a consistent custom-format database dump and save
uploads; restore into a disposable database to verify it. Existing `restic-main`
backup discovery includes PostgreSQL containers, Docker volumes and `/docker`.
Verify an offsite snapshot and restore; do not assume discovery proves a backup.
Never downgrade a migrated database without restoring a matching backup.

Disable the integration by clearing `NEWSLETTER_LIST_UUID` or reverting the PR.
Preserve Listmonk data and suppressions. CapRover app updates must preserve the
complete app definition; validate non-target fields, replicas and health after
any environment update. Deployments are complete only when both web and worker
are healthy on the intended revision.
