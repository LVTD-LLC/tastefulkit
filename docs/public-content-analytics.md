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

## Article-to-product engagement

Links inside a successfully rendered blog article's body also emit
`tastefulkit_marketing_cta_clicked`, with `cta_location=article_body` and the
article's existing `public_content_path`. This covers same-origin Explore,
Arena, rankings, UI-library and AI-skill directories, signup, MCP documentation,
and reference detail links. Detail destinations are route templates such as
`/ui-libraries/:id/`, never catalogue IDs. Query strings, fragments, link text,
external URLs and arbitrary/private paths are not collected by this handler.
Explicitly tagged links keep their existing handler and emit only once.

Compare article views with these clicks using the same production-host, time
window and QA/bot exclusions. A click is reference-exploration or signup intent,
not a completed destination view, verified email, save, successful API use or
activation. This coverage begins at deployment; earlier absent body-link events
cannot establish that readers never clicked. Blocked analytics remains unobserved.

The backend `tastefulkit_signup_completed` event is queued after a successful
signup form flow; it does not mean email verification or meaningful reference
use. Backend events do not currently supply the browser hostname or an article
identity. Do not join them to articles by time proximity or claim an organic
conversion rate. The browser privacy sanitizer also normalizes session-entry
URL/referrer fields to the current safe location, so those fields are not a
validated historical acquisition source. Acquisition and activation attribution
remain separate follow-up work.
