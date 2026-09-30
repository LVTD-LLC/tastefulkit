/** Prepared clips only; image fallback stays visible until playback succeeds. */
export function initMotion() {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const cards = [...document.querySelectorAll("[data-motion-card]")].map(root => {
    const video = root.querySelector("video");
    const button = root.querySelector("[data-motion-toggle]");
    button.hidden = false;
    return { root, video, button, visible: false, manual: 0, stopped: false, failed: false };
  });
  let manualOrder = 0;
  const label = card => {
    const playing = !card.video.paused;
    card.button.textContent = playing ? "Pause motion" : "Play motion";
    card.button.setAttribute("aria-label", `${playing ? "Pause" : "Play"} motion preview`);
    card.root.classList.toggle("is-playing", playing);
  };
  const play = card => {
    if (!card.video.getAttribute("src")) card.video.src = card.video.dataset.src;
    card.video.muted = true;
    // Rejected autoplay leaves an explicit play action, never an unhandled promise.
    card.video.play().catch(error => {
      if (error.name !== "AbortError") card.stopped = true;
      label(card);
    });
  };
  const reconcile = () => {
    const allowed = cards.filter(card => card.visible && !card.failed && !card.stopped &&
      (card.manual || (!reduced.matches && !navigator.connection?.saveData)));
    allowed.sort((a, b) => b.manual - a.manual);
    const active = document.hidden ? [] : allowed.slice(0, 2);
    for (const card of cards) {
      if (active.includes(card)) {
        if (card.video.paused) play(card);
      } else card.video.pause();
    }
  };
  const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(entries => {
    for (const entry of entries) {
      const card = cards.find(item => item.root === entry.target);
      card.visible = entry.isIntersecting && entry.intersectionRatio >= 0.5;
    }
    reconcile();
  }, { threshold: [0, 0.5] });
  for (const card of cards) {
    observer?.observe(card.root);
    card.video.addEventListener("playing", () => label(card));
    card.video.addEventListener("pause", () => label(card));
    card.video.addEventListener("error", () => {
      card.failed = true;
      card.video.pause();
      card.root.classList.remove("is-playing");
      card.button.textContent = "Preview unavailable";
      card.button.disabled = true;
      reconcile();
    });
    card.button.addEventListener("click", () => {
      card.stopped = !card.video.paused;
      card.manual = card.stopped ? 0 : ++manualOrder;
      if (!observer) card.visible = true;
      reconcile();
    });
  }
  reduced.addEventListener("change", () => {
    for (const card of cards) card.manual = false;
    reconcile();
  });
  document.addEventListener("visibilitychange", reconcile);

  for (const root of document.querySelectorAll("[data-motion-detail]")) {
    const video = root.querySelector("video");
    const buttons = [...root.querySelectorAll("[data-motion-view]")];
    const panels = [...root.querySelectorAll("[data-motion-panel]")];
    root.querySelector("[data-motion-switch]").hidden = false;
    const select = view => {
      for (const panel of panels) panel.hidden = panel.dataset.motionPanel !== view;
      for (const button of buttons) button.setAttribute("aria-pressed", String(button.dataset.motionView === view));
      if (view !== "video") video.pause();
    };
    for (const button of buttons) button.addEventListener("click", () => select(button.dataset.motionView));
    select("video"); // Detail playback is always user-initiated, including reduced-motion mode.
    video.addEventListener("error", () => { root.querySelector("[data-motion-error]").hidden = false; });
    video.querySelector("source")?.addEventListener("error", () => { root.querySelector("[data-motion-error]").hidden = false; });
    if (typeof IntersectionObserver !== "undefined") {
      new IntersectionObserver(entries => {
        if (!entries[0].isIntersecting) video.pause();
      }).observe(video);
    }
    document.addEventListener("visibilitychange", () => { if (document.hidden) video.pause(); });
  }
}
