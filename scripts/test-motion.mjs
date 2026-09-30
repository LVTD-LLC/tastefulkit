import assert from "node:assert/strict";
import test from "node:test";
import { initMotion } from "../frontend/src/js/modules/motion.js";

function setup({ reduced = false, saveData = false } = {}) {
  const events = target => Object.assign(target, {
    listeners: {},
    addEventListener(name, fn) { (this.listeners[name] ??= []).push(fn); },
    emit(name) { for (const fn of this.listeners[name] ?? []) fn(); },
  });
  const cards = Array.from({ length: 4 }, () => {
    const classes = new Set();
    const video = events({
      dataset: { src: "/clip.mp4" }, paused: true,
      getAttribute(name) { return this[name]; },
      play() { this.paused = false; this.emit("playing"); return Promise.resolve(); },
      pause() { this.paused = true; this.emit("pause"); },
    });
    const button = events({ setAttribute(name, value) { this[name] = value; } });
    return {
      video, button,
      classList: { toggle(name, on) { if (on) classes.add(name); else classes.delete(name); }, remove(name) { classes.delete(name); } },
      querySelector(selector) { return selector === "video" ? video : button; },
    };
  });
  let observer;
  globalThis.IntersectionObserver = class {
    constructor(fn) { observer = fn; }
    observe() {}
  };
  globalThis.window = { matchMedia: () => events({ matches: reduced }) };
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: { connection: { saveData } } });
  globalThis.document = events({
    hidden: false,
    querySelectorAll(selector) { return selector === "[data-motion-card]" ? cards : []; },
  });
  initMotion();
  const visible = shown => observer(cards.map((target, i) => ({ target, isIntersecting: shown.includes(i), intersectionRatio: shown.includes(i) ? 1 : 0 })));
  return { cards, visible, playing: () => cards.filter(c => !c.video.paused).length };
}

test("loads only two visible previews and pauses when offscreen/backgrounded", () => {
  const { cards, visible, playing } = setup();
  assert.ok(cards.every(c => !c.video.src));
  visible([0, 1, 2, 3]);
  assert.equal(playing(), 2);
  assert.ok(!cards[2].video.src && !cards[3].video.src);
  visible([2, 3]);
  assert.equal(playing(), 2);
  assert.ok(cards[0].video.paused && cards[1].video.paused);
  document.hidden = true;
  document.emit("visibilitychange");
  assert.equal(playing(), 0);
});

for (const preference of [{ reduced: true }, { saveData: true }]) {
  test(`preference ${JSON.stringify(preference)} prevents fetching until explicit play`, () => {
    const { cards, visible, playing } = setup(preference);
    visible([0, 1, 2, 3]);
    assert.equal(playing(), 0);
    assert.ok(cards.every(c => !c.video.src));
    cards[0].button.emit("click");
    assert.equal(playing(), 1);
    cards[0].button.emit("click");
    visible([0, 1]);
    assert.equal(playing(), 0);
  });
}

test("explicit playback gets priority without exceeding limit; errors retain fallback", () => {
  const { cards, visible, playing } = setup();
  visible([0, 1, 2, 3]);
  cards[2].button.emit("click");
  cards[3].button.emit("click");
  assert.equal(playing(), 2);
  assert.ok(!cards[2].video.paused && !cards[3].video.paused);
  cards[2].video.emit("error");
  assert.ok(cards[2].video.paused && cards[2].button.disabled);
  assert.ok(playing() <= 2);
});
