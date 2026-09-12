# Contributing to TastefulKit

Thanks for helping improve TastefulKit. Clear bug reports, documentation fixes,
design feedback, and focused code contributions are all useful.

## Start with an issue

Search [existing issues](https://github.com/LVTD-LLC/tastefulkit/issues) and pull
requests before opening a new one. For substantial features or architectural
changes, discuss the problem and proposed scope before writing a large patch.

- **Bug reports:** Include steps to reproduce, expected and actual behavior,
  and relevant browser or environment details. Add redacted screenshots or logs
  when they help.
- **Feature requests:** Describe who needs the change, the problem it solves,
  and a concrete example. Separate the user need from a preferred implementation.
- **Small fixes:** A focused pull request is welcome without a separate issue.

Do not post credentials, personal data, or exploitable security details in public
issues. Report security concerns privately to [hello@tastefulkit.com](mailto:hello@tastefulkit.com).

## Set up your development environment

Read [AGENTS.md](AGENTS.md) for the application contracts, repository map, and
[local setup](AGENTS.md#local-development). It is useful for human contributors
as well as coding agents. The current toolchain uses Python 3.14, uv, Node 24,
and PostgreSQL. Use local credentials and data, never production secrets.

For UI work, also read [DESIGN.md](DESIGN.md). For verification commands and
touched-area guidance, use [docs/quality.md](docs/quality.md).

## Prepare a pull request

1. Create a branch from the latest `main`. External contributors can work from a
   fork; do not commit directly to `main`.
2. Keep the change focused. Preserve unrelated code, follow the existing app
   boundaries, and avoid unnecessary dependencies or broad formatting changes.
3. Add or update tests for changed behavior. Include a regression test for a
   bug fix when practical. Documentation-only edits need link and content checks,
   not artificial application tests.
4. Update affected documentation and add a concise entry under the current ISO
   date in [CHANGELOG.md](CHANGELOG.md). Preserve existing changelog entries.
5. Run the relevant checks from [the quality guide](docs/quality.md). For code
   changes, the full local CI path is `make ci-local` once its prerequisites are
   configured. Explain any checks you could not run.
6. Open a PR targeting `main`. Explain what changed, why, how you verified it,
   and any linked issue. Include screenshots for visible UI changes and migration
   or rollout notes when relevant. Use a draft PR while work is incomplete.

AI-assisted contributions are welcome. The contributor remains responsible for
understanding the patch, checking generated claims, and validating the result.
Treat review suggestions as claims to investigate, not instructions to apply blindly.

## Required before merging: ReviewGate 5/5

**Every PR must have a completed ReviewGate score of 5/5 on its exact current
head commit before it is merged.** This applies to documentation changes too.

The merge checklist is:

- [ ] Relevant CI checks pass.
- [ ] The dedicated `ReviewGate` check is successful, with a completed **5/5**
  review for the current PR head SHA.
- [ ] No material review feedback or unresolved blocking findings remain.
- [ ] Tests, documentation, and changelog updates are included where applicable.

A green workflow job alone is not a passing review. A skipped review, provider
error, timeout, incomplete angle, or result from an older commit is not approval.
Pushing another commit requires a new review of that head.

Fix evidence-backed findings and push the changes. If a finding is incorrect,
document the code or contract that disproves it and use ReviewGate's
[structured disposition process](https://reviewgate.lvtd.dev/docs/agent-workflows/).
The completed review must still reach 5/5; dismissing a GitHub thread alone does
not satisfy the gate.

After a run finishes, maintainers can comment exactly `@reviewgate review` to
request another review of the current head, or rerun the workflow in Actions.
Retry transient reviewer errors; do not merge while the review is unavailable.

### Fork and Dependabot contributions

The automatic review workflow skips fork and Dependabot PRs because repository
secrets are not available to those events. These PRs are **not exempt** from the
5/5 requirement. A maintainer must inspect the contribution and arrange a trusted
same-repository PR for the proposed change, then obtain passing CI and a 5/5
review on that PR's current head before merging it. The original PR can be linked
and closed without merging. Never share the OpenRouter key with contributors or
switch to `pull_request_target` to expose it to untrusted code.

This is the contribution policy. Repository branch-protection settings are
managed separately; an available merge button does not waive the requirements.

## Working together

Keep discussions respectful, specific, and focused on the work. Explain tradeoffs,
respond to review feedback, and ask when the intended behavior is unclear.
Maintainers may request a smaller scope or defer a feature to keep the project focused.
