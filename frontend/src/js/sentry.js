import * as Sentry from "@sentry/browser";
import { optionsFor } from "./sentry-options.js";

const element = document.getElementById("sentry-config");
if (element) {
  try {
    const config = JSON.parse(element.textContent);
    const options = optionsFor(Sentry, config, window.location);
    Sentry.init(options);
    Sentry.logger.info("browser.monitoring.started", { route: config.route });
    Sentry.metrics.count("tastefulkit.browser.page_loaded", 1, { attributes: { route: config.route } });
  } catch {
    // Monitoring must never prevent the application from loading.
  }
}
