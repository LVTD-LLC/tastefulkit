# Changelog

## 2026-09-12

- Clarify the homepage search and social preview metadata around the shipped design-reference library, search, saved designs, API, and MCP; establish private Rowset-backed SEO run tracking.

- Rewrite the README for product users, move application engineering and operations details into AGENTS.md, and add contributor guidance requiring a current-head ReviewGate 5/5 before merge.

- Enable ReviewGate pull request reviews from its `main` branch, with general/adversarial checks, structured results, and maintainer-requested rereviews using the existing OpenRouter secret.

- Add authenticated hosted MCP at `/mcp/` in a dedicated Django app, sharing REST search, metadata, screenshot references, account info, and administrator submission/retry behavior. Include filter discovery, setup docs, revocation/permission/parity tests, and multi-worker ASGI serving.

- Enable configured PostHog analytics by default for visitors and signed-in users; remove the opt-in banner and account-event consent gates, migrate legacy opt-out state, and update analytics disclosures while preserving URL/property sanitization.

- Fix docs link hover so only the hovered link is underlined; restyle docs navigation in the warm, compact product language with a native mobile menu and accessible current-page state.

- Make all website documentation public and indexable, without changing library, account, or API authorization.
- Replace starter/deployment docs with guides to shipped browsing, search/filtering, saved-design, account, and read-only API features; keep operator references outside website routes.

- Adopt the approved reference-stack logo across public and app headers/footers, with theme-aware branding, matching browser/touch icons, and a first-party social preview.

- Fix Qdrant SDK client lifecycle handling discovered during live rollout; verify actual SDK cleanup in regression coverage.

- Move live embedding storage and similarity ranking to an isolated internal Qdrant service.
- Preserve authoritative catalogue filters, saved-design ownership, and visibility checks; retain keyword fallback.
- Add idempotent legacy-vector backfill, explicit regeneration, bounded indexing retries, and Qdrant health checks.
- Document persistent CapRover provisioning, recovery, and rollback; retain legacy vectors without querying them.

## 0.1.1 — 2026-09-12

- Pace screenshot captures and schedule bounded provider retries.
- Capture after DOM readiness and a short render settle, avoiding endless network-idle waits.
- Keep the interface functional when analytics is not configured.

## 0.1.0 — 2026-09-12

- Generate TastefulKit from the official djass template.
- Add design catalogue, private screenshot storage, background capture and embeddings.
- Add authenticated search, filters, saved designs, and admin-only ingestion/retry API.
- Remove automatic first-signup administrator promotion.
- Configure public GitHub repository and split CapRover web/worker deployment.
