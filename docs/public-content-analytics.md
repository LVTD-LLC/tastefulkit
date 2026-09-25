# Public content measurement

Published repository blog articles and successfully rendered public documentation
provide `public_content_path` on PostHog `$pageview` and
`tastefulkit_marketing_cta_clicked` events. The value is their canonical public
path, such as `/blog/landing-page-design-ideas/` or
`/docs/api-reference/mcp/`, without a query string or fragment.

Use this property to distinguish public content. Existing `route`, `$pathname`
and `$current_url` retain their sanitized route templates for compatibility.
Do not reconstruct an article from the old `/blog/:slug/` events: those events
cannot be attributed to individual articles retroactively.

Only successful content views supply the identity. Draft, future, missing and
private pages do not. The browser sanitizer restricts it to the matching public
content group/route and the two supported event types; it is not stored on
person profiles or in attribution cookies. HTMX navigation and browser history
update or clear the identity. Session recording remains disabled.

This provides page-level engagement measurement, not proof of organic
acquisition or a signup conversion. Marketing CTA clicks represent intent.
Session-entry attribution, backend signup success and meaningful reference-use
events need separately validated definitions before reporting a conversion rate.
Exclude `is_test_event=true` verification events from production analysis.
