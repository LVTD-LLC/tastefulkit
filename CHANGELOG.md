# Changelog

## 2026-09-12

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
