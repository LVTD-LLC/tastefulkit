import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { runInThisContext } from "node:vm";

import { initPosthogIdentity } from "../frontend/src/js/modules/posthog-identity.js";
import { initPosthogCtas } from "../frontend/src/js/modules/posthog-ctas.js";
import { sanitizePosthogEvent } from "../frontend/src/js/modules/posthog-privacy.js";
import { initPosthog } from "../frontend/src/js/modules/posthog.js";

const snippet = readFileSync(new URL("../frontend/templates/components/posthog.html", import.meta.url), "utf8");
const loadedBody = snippet.match(/loaded: function \(instance\) \{([\s\S]*?)\n {6}\},/)[1];
const sdkLoaded = runInThisContext(`(function (instance) {${loadedBody}})`);

function browser(cookie, identity = "") {
  const cookies = new Map(cookie ? [["analytics_consent", cookie]] : []);
  const listeners = {};
  const windowListeners = {};
  const captures = [];
  const identities = [];
  let optedOut = true;
  let distinctId = "anonymous-visitor";
  globalThis.document = {
    body: {
      dataset: { posthogPageviewEnabled: "true", posthogRoute: "/", posthogContentGroup: "marketing" },
      addEventListener(name, callback) { listeners[name] = callback; },
    },
    referrer: "https://example.org/article?private=value",
    addEventListener(name, callback) { listeners[name] = callback; },
    get cookie() { return [...cookies].map(([k, v]) => `${k}=${v}`).join("; "); },
    set cookie(value) {
      const [pair] = value.split(";");
      const [key, ...rest] = pair.split("=");
      if (value.includes("Max-Age=0")) cookies.delete(key);
      else cookies.set(key, rest.join("="));
    },
  };
  globalThis.window = {
    URL,
    location: { protocol: "https:", origin: "https://tastefulkit.com", pathname: "/", search: "?utm_source=test&token=private" },
    addEventListener(name, callback) { windowListeners[name] = callback; },
    dispatchEvent(event) { windowListeners[event.type]?.(event); },
    SaasAnalytics: { environment: "test", eventPrefix: "tastefulkit", identity: { distinctId: identity } },
    posthog: {
      clear_opt_in_out_capturing() { optedOut = false; },
      get_distinct_id() { return distinctId; },
      identify(id) { distinctId = id; identities.push(id); },
      setPersonProperties() {},
      capture(event, properties) {
        assert.equal(optedOut, false);
        captures.push(sanitizePosthogEvent({ event, properties }));
      },
    },
  };
  return { cookies, captures, identities, listeners, windowListeners };
}

for (const cookie of ["", "granted", "denied"]) {
  test(`pageviews and CTAs start without interaction (legacy choice: ${cookie || "none"})`, async () => {
    const state = browser(cookie);
    // A fresh pageview module models a full page load in each browser.
    const { initPosthogPageviews } = await import(`../frontend/src/js/modules/posthog-pageviews.js?case=${cookie}`);
    sdkLoaded(window.posthog);
    initPosthogIdentity();
    initPosthogPageviews();
    initPosthogCtas();
    assert.equal(state.cookies.has("analytics_consent"), false);
    assert.equal(state.captures.filter((e) => e.event === "$pageview").length, 1);
    assert.equal(state.captures[0].properties.$current_url, "https://tastefulkit.com/");
    assert.equal(state.captures[0].properties.utm_source, "test");
    assert.equal(state.captures[0].properties.$referrer, "https://example.org");
    assert.deepEqual(state.identities, []);
    assert.ok(state.cookies.has("marketing_attribution"));
    state.listeners.click({ target: { closest: () => ({ href: "/accounts/signup/?secret=private", dataset: { posthogCta: "signup", posthogCtaLocation: "header" } }) } });
    assert.equal(state.captures[1].event, "tastefulkit_marketing_cta_clicked");
    assert.equal(state.captures[1].properties.destination, "/accounts/signup/");
    assert.equal(JSON.stringify(state.captures).includes("private"), false);
  });
}

test("signed-in identity is linked automatically and logout still resets it", () => {
  const state = browser("denied", "42");
  let resets = 0;
  window.posthog.reset = () => { resets++; };
  initPosthog();
  assert.deepEqual(state.identities, []);
  assert.deepEqual(state.captures, []);
  sdkLoaded(window.posthog);
  initPosthog(); // Repeated startup must not duplicate identity or the initial pageview.
  assert.deepEqual(state.identities, ["42"]);
  assert.equal(state.captures.filter((e) => e.event === "$pageview").length, 1);
  state.listeners.submit({ target: { matches: () => true } });
  assert.equal(resets, 1);
});

test("private routes stay excluded and no-key pages remain functional", async () => {
  const state = browser("");
  document.body.dataset = {};
  const { initPosthogPageviews } = await import("../frontend/src/js/modules/posthog-pageviews.js?case=private");
  initPosthogIdentity();
  initPosthogPageviews();
  assert.deepEqual(state.captures, []);
  delete window.SaasAnalytics;
  delete window.posthog;
  assert.doesNotThrow(() => initPosthog());
});

test("public article identity survives navigation without exposing arbitrary URLs", async () => {
  const state = browser("");
  const dataset = (path) => ({
    posthogPageviewEnabled: "true", posthogRoute: "/blog/:slug/",
    posthogContentGroup: "blog", posthogPublicContentPath: path,
  });
  document.body.dataset = dataset("/blog/first-guide/");
  window.location.pathname = "/blog/first-guide/";
  window.DOMParser = class {
    parseFromString(text) { return { body: { dataset: JSON.parse(text.slice(6)) } }; }
  };
  const { initPosthogPageviews } = await import("../frontend/src/js/modules/posthog-pageviews.js?case=content");
  sdkLoaded(window.posthog);
  initPosthogPageviews();
  initPosthogCtas();
  assert.equal(state.captures[0].properties.public_content_path, "/blog/first-guide/");
  assert.equal(state.captures[0].properties.$pathname, "/blog/:slug/");
  state.listeners.click({ target: { closest: () => ({ href: "/accounts/signup/?token=secret", dataset: { posthogCta: "signup" } }) } });
  assert.equal(state.captures[1].properties.public_content_path, "/blog/first-guide/");
  window.location.pathname = "/blog/second-guide/";
  const xhr = { responseText: "<body>" + JSON.stringify(dataset("/blog/second-guide/")) };
  state.listeners["htmx:afterSwap"]({ detail: { xhr } });
  state.listeners["htmx:afterSwap"]({ detail: { xhr } });
  assert.equal(state.captures.filter((e) => e.event === "$pageview").length, 2);
  assert.equal(state.captures.at(-1).properties.public_content_path, "/blog/second-guide/");
  window.location.pathname = "/settings";
  state.listeners["htmx:afterSwap"]({ detail: { xhr: { responseText: "<body>{}" } } });
  const privateEvent = sanitizePosthogEvent({ event: "$pageview", properties: {
    public_content_path: "/blog/stale-secret/", $current_url: "https://tastefulkit.com/settings?token=secret",
  }, $set: { public_content_path: "/blog/stale-secret/" } });
  assert.equal(privateEvent.properties.public_content_path, undefined);
  assert.equal(privateEvent.$set.public_content_path, undefined);
  assert.equal(privateEvent.properties.$current_url, "https://tastefulkit.com");
  window.location.pathname = "/blog/first-guide/";
  state.windowListeners.popstate();
  assert.equal(state.captures.at(-1).properties.public_content_path, "/blog/first-guide/");
  window.location.pathname = "/unknown-private-path/";
  state.windowListeners.popstate();
  assert.equal(window.SaasAnalytics.pageviewContext.publicContentPath, "");
  assert.equal(JSON.stringify(state.captures).includes("secret"), false);
});

test("public content identity is scoped to successful content contexts and event types", () => {
  browser("");
  const context = { enabled: true, route: "/docs/:category/:page/", contentGroup: "docs",
    publicContentPath: "/docs/api-reference/mcp/" };
  window.SaasAnalytics.pageviewContext = context;
  window.location.pathname = "/docs/api-reference/mcp/";
  const event = { event: "$pageview", properties: { public_content_path: "untrusted" } };
  assert.equal(sanitizePosthogEvent(event).properties.public_content_path, "/docs/api-reference/mcp/");
  assert.equal(sanitizePosthogEvent({ ...event, event: "$set" }).properties.public_content_path, undefined);
  const personUpdate = sanitizePosthogEvent({ event: "$set", properties: {
    $set: { public_content_path: "/docs/api-reference/mcp/" },
    $set_once: { public_content_path: "/blog/private-slug/" },
  } });
  assert.equal(personUpdate.properties.$set.public_content_path, undefined);
  assert.equal(personUpdate.properties.$set_once.public_content_path, undefined);
  for (const path of ["/settings", "//evil.test/blog/x/", "/docs/api-reference/mcp/?key=secret", "/blog/other/", "/docs/a/b/#secret"]) {
    context.publicContentPath = path;
    assert.equal(sanitizePosthogEvent(event).properties.public_content_path, undefined);
  }
  context.publicContentPath = "/docs/api-reference/mcp/";
  context.enabled = false;
  assert.equal(sanitizePosthogEvent(event).properties.public_content_path, undefined);
});
