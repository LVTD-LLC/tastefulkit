# Change-only IndexNow notifications

Production deployment takes a complete snapshot of the live sitemap's public
pages before rollout, verifies the new deployment revision, then compares the
new snapshot. Only added, removed or changed pages are notified. An unchanged
site sends no request to IndexNow. A receipt is not proof of crawling or indexing.

The snapshot stores canonical public URLs and SHA-256 fingerprints, not HTML,
account data, CSRF tokens or signed image URLs. The fingerprint includes the
page title, search/social metadata, canonical, JSON-LD, main text, links and
image identities. It ignores runtime scripts, Sentry traces, CSRF inputs, CSS
build hashes, randomized Cloudflare email masks and expiring `X-Amz-*` asset signatures. CSS-only and runtime-only
changes therefore do not trigger notifications. This is a content-change signal,
not a visual comparison or a claim that all possible changes are detectable.

Fetching uses at most four concurrent requests. Failed, redirected, non-HTML or
missing-main pages and an inventory that changes during collection stop the
operation without posting or writing a partial snapshot. Fix the actual failure
before retrying; never substitute a smaller snapshot or fall back to all URLs.

## Verify without sending

```sh
python apps/pages/indexnow.py --site-url https://tastefulkit.com --snapshot before.json
# After the authorized content change and rollout:
python apps/pages/indexnow.py --site-url https://tastefulkit.com --previous before.json --dry-run
```

`--previous` is mandatory for a submission, including the Django
`submit_indexnow` management command. Version-1 content snapshots are required;
legacy JSON arrays of URLs cannot identify content changes and are rejected.
The deployment workflow creates the new snapshot before deploying, so no
bootstrap full-sitemap submission is necessary.

## Recover a failed notification

Download the original `indexnow-before-<sha>` workflow artifact and use the
**same checkout/script revision** that created it. Do not replace it with a
post-deployment snapshot: that would hide the change. Verify the intended live
revision and inspect the dry run first:

```sh
python apps/pages/indexnow.py --site-url https://tastefulkit.com --previous indexnow-before.json --expected-revision <deployed-sha> --dry-run
python apps/pages/indexnow.py --site-url https://tastefulkit.com --previous indexnow-before.json --expected-revision <deployed-sha>
```

Retry only a failed notification, not a successful receipt. A partial transport
failure may require replaying an already-received batch; this is bounded recovery,
not daily resubmission. There is no periodic crawler or new schedule. Changes
between deployments are not continuously monitored by this integration.

Tests: `uv run pytest apps/pages/test_indexnow.py -q`.
Protocol reference: <https://www.indexnow.org/documentation>.
