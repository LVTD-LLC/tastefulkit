# Reference brief builder verification

November 17, 2026. Screenshots use synthetic example/QA notes, not customer data.
The browser exercised the actual Django-rendered page and built static modules.
The disposable preview omits database-backed banner, newsletter and provider
context only; hosted CI tests the production configuration and database.

## States

- Default: [mobile light](390-light-default.png), [desktop dark](1440-dark-default.png).
- User result: [mobile dark](390-dark-useroutput.png), [desktop light](1440-light-useroutput.png).
- Invalid: [empty required field](390-light-empty.png), [malformed source URL](390-light-malformed.png), [over-limit field](390-light-boundary.png).
- Recovery: [clipboard unavailable](390-light-clipboard-failure.png), [download unavailable with result retained](390-dark-download-recovery.png).

Parent Chromium checks covered 390/1440 px in light/dark. An independent runtime
review operated mobile dark and desktop light, including keyboard focus/order,
blank and whitespace entries, URL validation, decision changes, stale-result
clearing, refresh reset and forced clipboard/download failures. No horizontal
overflow or page exceptions were observed. Copy failure leaves selectable text.

The download event, fixed filename and exact browser Blob contents were checked.
Browserless/CDP could not copy its remote download artifact to the operator's
local filesystem (ENOENT). Native artifact transport is therefore unverified;
it is not reported as a passing download-to-disk check. The result remains
available for manual copying.

No source fetching, AI request, saved result URL or persistence is part of this
tool. Optional fields stay explicitly unknown; exported acceptance tasks begin
NOT CHECKED. The tool does not verify supplied facts or approve third-party reuse.
