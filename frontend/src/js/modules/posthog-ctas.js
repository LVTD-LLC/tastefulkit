const articleDestinations = new Map([
  ["/explore/", "explore"],
  ["/arena/", "arena"],
  ["/rankings/", "rankings"],
  ["/ui-libraries/", "ui_libraries"],
  ["/ai-skills/", "ai_skills"],
  ["/accounts/signup/", "signup"],
  ["/docs/api-reference/mcp/", "mcp_docs"],
]);

function articleCta(element) {
  const context = window.SaasAnalytics?.pageviewContext;
  if (!element || !context?.enabled || context.contentGroup !== "blog" ||
      context.route !== "/blog/:slug/" ||
      context.publicContentPath !== window.location.pathname ||
      !/^\/blog\/[a-z0-9]+(?:-[a-z0-9]+)*\/$/.test(context.publicContentPath || "") ||
      !element.closest?.(".tk-blog-body")) return null;

  try {
    const url = new window.URL(element.href, window.location.origin);
    if (url.origin !== window.location.origin || url.username || url.password) return null;
    const name = articleDestinations.get(url.pathname);
    if (name) return { name, destination: url.pathname };
    const detail = url.pathname.match(
      /^\/(designs|ui-libraries|ai-skills)\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/$/i,
    );
    if (detail) return { name: "reference_detail", destination: `/${detail[1].toLowerCase()}/:id/` };
  } catch (_error) {
    // Only known same-origin public destinations are eligible.
  }
  return null;
}

function captureCta(element, article = null) {
  const analytics = window.SaasAnalytics;
  if (!element || !analytics) return;

  let destination = "";
  try {
    destination = article?.destination ||
      new window.URL(element.href || element.action, window.location.origin).pathname;
  } catch (_error) {
    // Invalid destinations use the empty allowlisted value.
  }

  window.posthog?.capture?.(`${analytics.eventPrefix}_marketing_cta_clicked`, {
    event_version: 1,
    environment: analytics.environment || "unknown",
    cta_name: article?.name || element.dataset.posthogCta,
    cta_location: article ? "article_body" : element.dataset.posthogCtaLocation || "unknown",
    destination,
  });
}

export function initPosthogCtas() {
  document.addEventListener("click", (event) => {
    const explicit = event.target.closest?.("a[data-posthog-cta]");
    if (explicit) {
      captureCta(explicit);
      return;
    }
    const link = event.target.closest?.("a[href]");
    const article = articleCta(link);
    if (article) captureCta(link, article);
  });
  document.addEventListener("submit", (event) => {
    captureCta(event.target.closest?.("form[data-posthog-cta]"));
  });
}
