# Dialog form ownership specimen

A deliberately failing composition and a corrected composition for the
[TastefulKit Svelte-library guide](https://tastefulkit.com/blog/best-svelte-ui-libraries/).
This is an isolated learning example, not application code or a booking service.
It sends no data and uses only synthetic customer details. Do not enter real data.

## Run locally

Use Node 24, then run these commands from this directory (not the repo root):

```sh
npm ci --include=dev
npm run dev
```

Open the local URL printed by Vite. This fixture pins Svelte 5.57.2 and Bits UI
2.20.2. Its composition follows the official
[Bits UI dialog/form guidance](https://www.bits-ui.com/docs/components/dialog#working-with-forms)
and [Select submission API](https://www.bits-ui.com/docs/components/select#selectroot).
The submit handler and layout switch are original diagnostic scaffolding.
The Vite entry point follows the [Svelte mount API](https://svelte.dev/docs/svelte/imperative-component-api#mount).

## Repeat the check

1. Keep **Outer form with portal** selected. Open the dialog and choose a service.
   Inspect the customer input and hidden service input in browser developer
   tools: their `form` property is null. Click **Book appointment**; this
   portalled button also has no native form owner and cannot submit that form.
   Click **Inspect outer form data** while the dialog is still open. This explicit diagnostic
   constructs `FormData` from the outer form and displays an empty object (`{}`).
   This is a field-capture check, not a server submission.
2. Cancel, switch to **Form inside dialog**, reopen and choose **Review**. Change the synthetic customer name.
   Submit. The captured payload includes `customer` and `service` values.
   A local simulated rejection leaves the dialog open with the details intact.
3. Cancel and confirm that focus returns to **Choose appointment**.

Checked in isolated Chromium on October 24, 2026. This is one Svelte/Bits UI
composition, not a cross-library comparison, backend-validation test,
mobile certification, performance benchmark or assistive-technology audit.
The rejection is synchronous local scaffolding, not an HTTP failure simulation.
Production implementations still need server validation, pending/error states,
responsive checks and their own keyboard/assistive-technology review.
Do not nest one HTML form inside another to solve the ownership boundary.
