# TastefulKit — current product claims

Verified September 24, 2026 against main commit `01591c25c6ee8880ddd8a81569e79316ea8c5576` ([PR #30](https://github.com/LVTD-LLC/tastefulkit/pull/30)) and public docs. Private historical claim observations remain in the existing Rowset research dataset; this is public source-backed guidance, not a replacement history.

| Claim | Current value | Source | Read date | Risk |
|---|---|---|---|---|
| Current feature access | All current features are free. Full catalogue, saves, guides and personal rankings require an account; no subscription is required. | `apps/catalogue/views.py`, `apps/catalogue/arena_views.py`, `/pricing/`, `/docs/using-tastefulkit/browsing/` | 2026-09-24 | High: access/pricing |
| API and MCP access | Personal API key for an active account; no paid membership check. MCP remains read-only. | `apps/api/auth.py`, `apps/hosted_mcp/auth.py`, `/docs/api-reference/mcp/` | 2026-09-24 | High: access |
| Public comparison | Arena voting and global rankings work without an account; preference does not establish conversion performance. | `apps/catalogue/arena_views.py`, `/docs/using-tastefulkit/browsing/` | 2026-09-24 | Medium |

Do not promise free forever or automatic cancellation of existing subscriptions. Do not remove account, API-key or administrator-only ingestion boundaries. Mechanical public-copy checks live in `truth-checks.json`.
