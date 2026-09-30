# TastefulKit — current product claims

Verified September 30, 2026 against the free-access release in [PR #36](https://github.com/LVTD-LLC/tastefulkit/pull/36) and automatic-key provisioning in [PR #44](https://github.com/LVTD-LLC/tastefulkit/pull/44). Sources below describe the implementation in this repository. Private historical claim observations remain in the existing Rowset research dataset; this is current guidance, not a replacement history.

| Claim | Current value | Source | Read date | Risk |
|---|---|---|---|---|
| Current feature access | All current features, including available DESIGN.md guides, are free. Full catalogue, saves, screenshots, personal rankings and guides require an active account, not a subscription. | `apps/catalogue/views.py`, `apps/catalogue/arena_views.py`, `/pricing/`, `/docs/using-tastefulkit/browsing/` | 2026-09-30 | High: access/pricing |
| API and MCP access | Personal API key for an active account. Metadata, screenshots and available DESIGN.md text are free. Keys are provisioned automatically; explicit rotation invalidates previous keys. MCP remains read-only. | `apps/core/models.py`, `apps/core/signals.py`, `apps/api/auth.py`, `apps/hosted_mcp/auth.py`, `apps/catalogue/services.py`, `/docs/api-reference/mcp/` | 2026-09-30 | High: access |
| Public comparison | Arena voting and global rankings work without an account; preference does not establish conversion performance. | `apps/catalogue/arena_views.py`, `/docs/using-tastefulkit/browsing/` | 2026-09-30 | Medium |

Do not promise free forever or automatic cancellation of existing subscriptions. Do not remove account, API-key or administrator-only ingestion boundaries. Mechanical public-copy checks live in `truth-checks.json`.
