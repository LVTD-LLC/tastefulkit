# TastefulKit — current product claims

Updated September 24, 2026 for the paid-guide policy in [PR #33](https://github.com/LVTD-LLC/tastefulkit/pull/33). Sources below describe the implementation in this repository. Private historical claim observations remain in the existing Rowset research dataset; this is current guidance, not a replacement history.

| Claim | Current value | Source | Read date | Risk |
|---|---|---|---|---|
| Current feature access | Full catalogue, saves, screenshots and personal rankings are free with an account. Only DESIGN.md guides require an active $10/month membership. | `apps/catalogue/views.py`, `apps/catalogue/arena_views.py`, `/pricing/`, `/docs/using-tastefulkit/browsing/` | 2026-09-24 | High: access/pricing |
| API and MCP access | Personal API key for an active account. Metadata/screenshots are free; DESIGN.md text requires paid access. MCP remains read-only. | `apps/api/auth.py`, `apps/hosted_mcp/auth.py`, `apps/catalogue/services.py`, `/docs/api-reference/mcp/` | 2026-09-24 | High: access |
| Public comparison | Arena voting and global rankings work without an account; preference does not establish conversion performance. | `apps/catalogue/arena_views.py`, `/docs/using-tastefulkit/browsing/` | 2026-09-24 | Medium |

Do not promise free forever or automatic cancellation of existing subscriptions. Do not remove account, API-key or administrator-only ingestion boundaries. Mechanical public-copy checks live in `truth-checks.json`.
