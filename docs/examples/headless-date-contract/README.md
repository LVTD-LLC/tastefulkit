# Date display and submission specimen

An isolated companion to the [TastefulKit headless-library guide](https://tastefulkit.com/blog/best-headless-ui-libraries/).
This is synthetic local scaffolding, not a booking application. It sends no data.

## Run locally

Use Node 24. From this directory, not the repository root, run:

```sh
npm ci --include=dev
npm run dev
```

Open the local URL Vite prints. Dependencies are pinned: React/React DOM 19.3.1,
React Aria Components 1.22.1 and `@internationalized/date` 3.12.4.
The component composition, `I18nProvider`, `name`, date parsing and display
settings follow the official [DatePicker documentation](https://react-aria.adobe.com/DatePicker)
and [date-value documentation](https://react-spectrum.adobe.com/internationalized/date/index.html).
The two-field comparison and `FormData` capture are original diagnostic scaffolding;
see [FormData](https://developer.mozilla.org/en-US/docs/Web/API/FormData/FormData).
The commands use the [Vite CLI](https://vite.dev/guide/cli) (8.3.5 in this specimen).

## Repeat the check

1. Submit the prefilled form. Both date inputs display November 5, 2026.
   `booking_day` contains `2026-11-05`; `appointment` contains
   `2026-11-05T09:30:00-08:00[America/Los_Angeles]`.
2. Switch the display locale between US and UK English and submit again.
   The date segment order changes, but the captured payloads do not.
3. Repeat in browser contexts configured for Los Angeles and Tokyo. The supplied
   calendar date and named-zone appointment remain the same in this fixture.

The day-only setting intentionally hides the appointment's time to expose the
value/display boundary. It is not a recommended appointment UI. A real customer
must be able to inspect and confirm the time and zone before submitting.

Only prefilled-value submission and locale switching were exercised; editing date
segments and opening or navigating the calendar were not part of this check.

Checked in isolated Chromium on October 26, 2026, across those two display locales
and two browser time zones. No comparison across libraries, daylight-saving
transition, invalid/cleared input, backend, mobile, performance or
assistive-technology certification is implied. Test those separately before
adopting a wrapper in your application. There are no real customer records.
