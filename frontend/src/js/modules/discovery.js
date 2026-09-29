export function initDiscoveryNavigation() {
  document.querySelectorAll(".tk-discovery-nav .tk-tabs").forEach((nav) => {
    const active = nav.querySelector("[aria-current]");
    if (!active) return;
    const bounds = nav.getBoundingClientRect();
    const selected = active.getBoundingClientRect();
    // Reveal the current type without moving the document or stealing focus.
    if (selected.left < bounds.left || selected.right > bounds.right) {
      nav.scrollLeft += selected.left - bounds.left - 4;
    }
  });
}
