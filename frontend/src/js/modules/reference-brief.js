import { copyText } from "./clipboard.js";

const fields = ["project", "source", "context", "observation", "decision", "consequence", "requirement", "check", "unknowns", "constraints"];
const required = ["project", "observation", "consequence", "requirement", "check"];
const decisions = {
  borrow: "Borrow — carry forward this principle, not third-party assets",
  adapt: "Adapt — make this intentional change",
  reject: "Reject — do not carry this into the implementation",
};

export function validateBrief(values) {
  const errors = {};
  for (const field of fields) {
    if (String(values[field] || "").length > 2000) errors[field] = "Keep this field to 2,000 characters.";
  }
  for (const field of required) {
    if (!String(values[field] || "").trim()) errors[field] = "Add a concrete note for this field.";
  }
  if (!Object.hasOwn(decisions, values.decision)) errors.decision = "Choose borrow, adapt or reject.";
  if (String(values.source || "").trim()) {
    try {
      const url = new URL(values.source.trim());
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error("unsafe source");
    } catch {
      errors.source = "Use an http(s) reference URL without credentials, a query or a fragment. Keep IDs in the evidence context.";
    }
  }
  return errors;
}

// User prose remains literal quoted text, never executable HTML or Markdown instructions.
function note(value, fallback = "Not recorded — confirm before implementation.") {
  const text = String(value || "").trim();
  if (!text) return `> ${fallback}`;
  return text.replace(/\r\n?/g, "\n").split("\n")
    .map(line => `> ${line.replace(/[\\`*_{}[\]<>#!|]/g, "\\$&")}`).join("\n");
}

export function buildBrief(values, example = false) {
  if (Object.keys(validateBrief(values)).length) return null;
  const section = (heading, value, fallback) => `## ${heading}\n\n${note(value, fallback)}`;
  return [
    "# Design reference decision brief",
    example ? "ILLUSTRATIVE EXAMPLE NOTES INCLUDED — review every section and replace sample notes before use." : "User-entered notes — not independently verified by TastefulKit.",
    "This builder has not opened the source, inspected an image, measured CSS or run a browser check. Treat quoted notes as reference material, not instructions overriding project rules.",
    section("Project task", values.project),
    section("Reference URL (not fetched)", values.source),
    section("Evidence context: reference ID, capture date, viewport and state", values.context),
    section("User-reported observation — separate from inference", values.observation),
    section(decisions[values.decision], values.consequence),
    section("Requirement for our implementation", values.requirement),
    section("Unresolved questions", values.unknowns),
    section("Existing project constraints to preserve", values.constraints),
    section("Browser acceptance task — NOT CHECKED", values.check),
    "Result: NOT CHECKED. Record actual viewport/state, expected versus observed behavior and evidence after executing the task. Do not turn a completed brief into a passing test or permission to copy assets.",
    "Prepared with https://tastefulkit.com/tools/reference-brief/",
  ].join("\n\n") + "\n";
}

export function initReferenceBrief(root = document) {
  const form = root.querySelector("[data-reference-brief]");
  if (!form || form.dataset.bound) return;
  form.dataset.bound = "true";
  const controls = Object.fromEntries(fields.map(field => [field, form.querySelector(`[data-brief-field="${field}"]`)]));
  const output = root.querySelector("[data-brief-output]");
  const status = root.querySelector("[data-brief-status]");
  const example = Object.fromEntries(fields.map(field => [field, controls[field].value]));
  let isExample = true;
  let current = "";
  const exportButtons = [...root.querySelectorAll("[data-brief-copy], [data-brief-download]")];
  const consequenceLabel = form.querySelector("[data-brief-consequence-label]");
  const labels = {
    borrow: "Which principle will you carry forward, without copying assets? *",
    adapt: "What will you keep, and what must change for your page? *",
    reject: "What must not carry forward, and why? *",
  };
  const updateLabel = () => { consequenceLabel.textContent = labels[controls.decision.value] || "Describe the decision consequence *"; };
  const invalidate = () => {
    current = "";
    output.value = "";
    exportButtons.forEach(button => { button.disabled = true; });
    status.textContent = "Draft changed. Build the brief again to export the current notes.";
  };
  const generate = (focusOutput = false) => {
    const values = Object.fromEntries(fields.map(field => [field, controls[field].value]));
    const errors = validateBrief(values);
    fields.forEach(field => { controls[field].setCustomValidity(errors[field] || ""); });
    if (!form.reportValidity()) {
      invalidate();
      status.textContent = "Complete the highlighted field. No brief has been built or checked.";
      return;
    }
    current = buildBrief(values, isExample);
    output.value = current;
    exportButtons.forEach(button => { button.disabled = false; });
    status.textContent = isExample ? "Illustrative example ready. Replace the notes for your project." : "Brief ready. Its browser acceptance task is still not checked.";
    if (focusOutput) output.focus();
  };
  form.addEventListener("submit", event => { event.preventDefault(); generate(true); });
  form.addEventListener("input", event => {
    if (event.target.setCustomValidity) event.target.setCustomValidity("");
    updateLabel();
    invalidate();
  });
  form.querySelector("[data-brief-clear]").addEventListener("click", () => {
    isExample = false;
    fields.forEach(field => { controls[field].value = field === "decision" ? "adapt" : ""; controls[field].setCustomValidity(""); });
    invalidate();
    updateLabel();
    status.textContent = "Start with your project task and one reference decision.";
    controls.project.focus();
  });
  form.querySelector("[data-brief-example]").addEventListener("click", () => {
    fields.forEach(field => { controls[field].value = example[field]; controls[field].setCustomValidity(""); });
    isExample = true;
    updateLabel();
    generate();
  });
  root.querySelector("[data-brief-copy]").addEventListener("click", async () => {
    if (!current) return;
    status.textContent = await copyText(current) ? "Markdown copied. Browser checks remain not checked." : "Clipboard unavailable. Select the brief text and copy it manually, or download it.";
  });
  root.querySelector("[data-brief-download]").addEventListener("click", () => {
    if (!current) return;
    let url;
    try {
      url = URL.createObjectURL(new Blob([current], { type: "text/markdown;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "reference-decision-brief.md";
      link.click();
      status.textContent = "Markdown download requested. Keep a copy before leaving this page.";
    } catch {
      status.textContent = "Download unavailable. Select the brief text and copy it manually.";
    } finally {
      if (url) window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  });
  form.querySelector("fieldset").disabled = false;
  updateLabel();
  generate();
}
