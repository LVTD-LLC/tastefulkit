import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";
import test from "node:test";
const source = await readFile("frontend/src/js/sentry-options.js", "utf8");
const { optionsFor, scrubEvent } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const Sentry = { browserTracingIntegration: (options) => options, replayIntegration: (options) => options };
const config = { replayEnabled: true, route: "landing", replaysSessionSampleRate: 0.1, replaysOnErrorSampleRate: 1 };
const location = { origin: "https://tastefulkit.com", search: "", hash: "" };
test("replay masks content, drops network events and excludes private visits", () => {
  const opts = optionsFor(Sentry, config, location);
  assert.equal(opts.integrations[1].maskAllText, true);
  assert.equal(opts.integrations[1].maskAllInputs, true);
  assert.equal(opts.integrations[1].networkCaptureBodies, false);
  assert.equal(opts.integrations[1].beforeAddRecordingEvent({ type: 5 }), null);
  for (const loc of [{ ...location, search: "?key=secret" }, { ...location, hash: "#secret" }]) {
    assert.equal(optionsFor(Sentry, config, loc).replaysOnErrorSampleRate, 0);
  }
  assert.equal(optionsFor(Sentry, { ...config, replayEnabled: false }, location).integrations.length, 1);
  assert.equal(opts.tracePropagationTargets.some((rule) => rule.test("https://evil.com/")), false);
  assert.equal(opts.tracePropagationTargets.some((rule) => rule.test("//evil.com/")), false);
  assert.equal(opts.tracePropagationTargets.some((rule) => rule.test("https://tastefulkit.com/api/")), true);
});
test("errors and traces remove request, query, messages and span data", () => {
  const event = scrubEvent({ request: { headers: "secret" }, user: { email: "secret" }, message: "secret", extra: { key: "secret" }, breadcrumbs: ["secret"], exception: { values: [{ value: "secret", stacktrace: { frames: [{ filename: "https://tastefulkit.com/static/js/app.js?secret" }] } }] }, spans: [{ description: "secret", data: { key: "secret" } }] });
  assert.equal(JSON.stringify(event).includes("secret"), false);
});
