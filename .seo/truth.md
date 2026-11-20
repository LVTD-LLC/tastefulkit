# TastefulKit — current product claims

Verified October 1, 2026 against public Explore and full-detail access in [PR #50](https://github.com/LVTD-LLC/tastefulkit/pull/50), the How to Use guide in [PR #49](https://github.com/LVTD-LLC/tastefulkit/pull/49), and automatic-key provisioning in [PR #44](https://github.com/LVTD-LLC/tastefulkit/pull/44). Sources below describe the implementation in this repository. Private historical claim observations remain in the existing Rowset research dataset; this is current guidance, not a replacement history.

| Claim | Current value | Source | Read date | Risk |
|---|---|---|---|---|
| Current feature access | All current features are free. Published ready catalogue pages/components, full screenshots, metadata and available DESIGN.md viewing/copying/downloads are public. Saves and personal rankings require a free active account, not a subscription. | `apps/catalogue/views.py`, `apps/catalogue/arena_views.py`, `/pricing/`, `/docs/using-tastefulkit/browsing/` | 2026-10-01 | High: access/pricing |
| API and MCP access | Personal API key for an active account. Metadata, screenshots and available DESIGN.md text are free. Keys are provisioned automatically; signed-in users can copy their installation prompt from How to Use. Explicit rotation invalidates previous keys. MCP remains read-only. | `apps/core/models.py`, `apps/core/signals.py`, `apps/api/auth.py`, `apps/hosted_mcp/auth.py`, `apps/catalogue/services.py`, `/docs/api-reference/mcp/` | 2026-10-01 | High: access |
| Public comparison | Arena voting and global rankings work without an account; preference does not establish conversion performance. | `apps/catalogue/arena_views.py`, `/docs/using-tastefulkit/browsing/` | 2026-10-01 | Medium |

Do not promise free forever or automatic cancellation of existing subscriptions. Preserve account boundaries for saves/personal rankings, API-key authentication and administrator-only ingestion. Mechanical public-copy checks live in `truth-checks.json`.

## Dated external-library claims

| Claim | Current value | Source | Read date | Risk |
|---|---|---|---|---|
| Oat release status | Oat is no longer pre-v1; v1.1.0 was published November 1, 2026. This is a dated release observation, not an integration guarantee. | [Official v1.1.0 release](https://github.com/knadh/oat/releases/tag/v1.1.0), [usage guide](https://oat.ink/usage/) | 2026-11-16 | Medium: library selection |
| Nuxt UI server-rendered Markdown patch | The maintainer identifies Nuxt UI 4.12.2 as the complete fix for GHSA-x9jw-j844-v24h. Scope is apps rendering untrusted Markdown server-side through the affected stack, not TastefulKit's Django blog. | [Official Nuxt UI 4.12.2 release](https://ui.nuxt.com/docs/releases/v4.12.2), [Nuxt UI 4.12.1 update guidance](https://ui.nuxt.com/docs/releases/v4.12.1) | 2026-11-20 | High: dependency guidance |
