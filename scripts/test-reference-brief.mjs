import assert from "node:assert/strict";
import test from "node:test";
import { buildBrief, validateBrief } from "../frontend/src/js/modules/reference-brief.js";

const values = { project: "Agency plans", source: "https://example.com/pricing", context: "1440 px, screenshot only", observation: "Unit beside amount", decision: "adapt", consequence: "Use agency, not seat", requirement: "Attach approved unit to amount", check: "At 390 px locate unit without a tooltip" };

test("export retains the decision, missing evidence and explicitly unperformed task", () => {
  for (const decision of ["borrow", "adapt", "reject"]) {
    const result = buildBrief({ ...values, decision });
    assert.match(result, new RegExp(`## ${decision[0].toUpperCase() + decision.slice(1)}`));
    assert.match(result, /Use agency, not seat/);
    assert.match(result, /Not recorded — confirm before implementation/);
    assert.match(result, /Browser acceptance task — NOT CHECKED/);
    assert.match(result, /not opened the source/);
    assert.match(result, /1440 px, screenshot only/);
  }
});

test("incomplete, malformed and over-limit notes cannot generate an apparent result", () => {
  assert.equal(buildBrief({}), null);
  for (const project of ["", "  \n  ", "a".repeat(2001)]) assert.equal(buildBrief({ ...values, project }), null);
  for (const source of ["invalid", "javascript:alert(1)", "https://user:secret@example.com/", "https://example.com/?key=secret", "https://example.com/#secret"]) {
    assert.ok(validateBrief({ ...values, source }).source);
    assert.equal(buildBrief({ ...values, source }), null);
  }
  assert.equal(buildBrief({ ...values, decision: "passed" }), null);
});

test("literal Unicode, numeric-looking notes, boundaries and HTML do not become invented facts or markup", () => {
  for (const project of ["東京 — مثال 🎨", "0", "-1", "a".repeat(2000)]) assert.ok(buildBrief({ ...values, project }));
  const result = buildBrief({ ...values, source: "", observation: "  <script>alert(1)</script>\r\n# fake heading\n[bad](javascript:alert(1))  " });
  assert.ok(!result.includes("<script>"));
  assert.ok(!result.includes("\n# fake heading"));
  assert.match(result, /not fetched/);
  assert.match(buildBrief(values, true), /ILLUSTRATIVE EXAMPLE/);
});
