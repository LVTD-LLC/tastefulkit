async function loadFullScreenshots(form) {
  const previews = [...form.querySelectorAll("[data-arena-full-src]")].filter(
    (preview) => preview.src !== new URL(preview.dataset.arenaFullSrc, document.baseURI).href,
  );
  // Get both lightweight choices on screen before competing for image bandwidth.
  await Promise.allSettled(previews.map((preview) => preview.decode()));
  await Promise.all(previews.map(async (preview) => {
    const full = new Image();
    full.fetchPriority = "low";
    full.decoding = "async";
    full.src = preview.dataset.arenaFullSrc;
    try {
      await full.decode();
      // Swap only once decoded, keeping the preview visible if the full image fails.
      preview.src = full.src;
    } catch {
      // A lightweight preview is still a usable voting choice.
    }
  }));
}

export function initArena() {
  const form = document.querySelector("[data-arena-form]");
  if (!form) return;
  void loadFullScreenshots(form);
  form.addEventListener("submit", (event) => {
    if (form.dataset.submitting) {
      event.preventDefault();
      return;
    }
    const submitter = event.submitter;
    if (!submitter) return;
    const choice = document.createElement("input");
    choice.type = "hidden";
    choice.name = submitter.name;
    choice.value = submitter.value;
    choice.dataset.pendingChoice = "true";
    form.append(choice);
    form.dataset.submitting = "true";
    form.setAttribute("aria-busy", "true");
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
      button.disabled = true;
    });
  });
  window.addEventListener("pageshow", (event) => {
    // A navigation can interrupt background downloads before they finish.
    if (event.persisted) void loadFullScreenshots(form);
    delete form.dataset.submitting;
    form.removeAttribute("aria-busy");
    form.querySelectorAll("[data-pending-choice]").forEach((input) => input.remove());
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
      button.disabled = false;
    });
  });
}
