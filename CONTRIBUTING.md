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

## Working together

Keep discussions respectful, specific, and focused on the work. Explain tradeoffs,
respond to review feedback, and ask when the intended behavior is unclear.
Maintainers may request a smaller scope or defer a feature to keep the project focused.
