export function initArena() {
  const form = document.querySelector("[data-arena-form]");
  if (!form) return;
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
  window.addEventListener("pageshow", () => {
    delete form.dataset.submitting;
    form.removeAttribute("aria-busy");
    form.querySelectorAll("[data-pending-choice]").forEach((input) => input.remove());
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
      button.disabled = false;
    });
  });
}
