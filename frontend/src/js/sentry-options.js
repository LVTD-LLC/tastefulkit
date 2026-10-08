export function scrubEvent(event) {
  delete event.user;
  delete event.extra;
  delete event.breadcrumbs;
  delete event.message;
  delete event.request;
  for (const exception of event.exception?.values || []) {
    exception.value = "[Filtered: inspect stack trace]";
    for (const frame of exception.stacktrace?.frames || []) {
      if (frame.filename) frame.filename = frame.filename.split(/[?#]/)[0];
      delete frame.vars;
    }
  }
  for (const span of event.spans || []) {
    span.description = span.op || "operation";
    span.data = {};
  }
  if (event.contexts?.trace) delete event.contexts.trace.data;
  return event;
}

export function optionsFor(Sentry, config, location) {
  const replay = config.replayEnabled && !location.search && !location.hash;
  return {
    dsn: config.dsn,
    environment: config.environment,
    release: config.release || undefined,
    sendDefaultPii: false,
    enableLogs: true,
    tracesSampleRate: config.tracesSampleRate,
    // Never propagate headers to storage, analytics, Sentry, or other origins.
    tracePropagationTargets: [new RegExp(`^${location.origin.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/`), /^\/(?!\/)/],
    replaysSessionSampleRate: replay ? config.replaysSessionSampleRate : 0,
    replaysOnErrorSampleRate: replay ? config.replaysOnErrorSampleRate : 0,
    integrations: [
      Sentry.browserTracingIntegration({
        beforeStartSpan: (span) => ({ ...span, name: config.route, attributes: {} }),
      }),
      ...(replay ? [Sentry.replayIntegration({
        maskAllText: true, maskAllInputs: true, blockAllMedia: true,
        block: ["script", "[data-sentry-block]"],
        networkDetailAllowUrls: [], networkCaptureBodies: false,
        // Remove console/network breadcrumbs, which may include private URLs.
        beforeAddRecordingEvent: (event) => event.type === 5 ? null : event,
      })] : []),
    ],
    beforeSend: scrubEvent,
    beforeSendTransaction: (event) => { event.transaction = config.route; return scrubEvent(event); },
    beforeBreadcrumb: () => null,
    beforeSendLog: (log) => log.message === "browser.monitoring.started" ? log : null,
    beforeSendMetric: (metric) => metric.name === "tastefulkit.browser.page_loaded" ? metric : null,
  };
}
