# Lessons

Durable correction log for this repository.

## 2026-05-29

Pattern: The repository originally had live Steam API integration tests in the default test path.

Rule: Keep live API tests marked as `integration` and excluded from the fast default CI/test suite unless explicitly requested.

Pattern: Local Python and network commands may require the approved elevated execution path in this Windows workspace.

Rule: If a command fails with sandbox, socket, or WindowsApps alias errors, verify whether the same command needs approved execution rather than assuming a project failure.

Pattern: Release automation can fail separately from the main package workflow.

Rule: Treat release workflow failures as their own task. Do not conflate them with source checks if the main branch CI passes.

Pattern: The user wants GitHub pushes to require explicit approval each time, even when GitHub auth is configured and previous pushes succeeded.

Rule: Never run `git push`, create/update GitHub releases, or otherwise publish remote changes without asking the user for explicit approval in that turn.

Pattern: Releases must use Semantic Versioning and version-specific release notes before any remote publishing.

Rule: For every release, choose `MAJOR.MINOR.PATCH`, create release notes for that exact version, prepare local commit/tag first, then stop for explicit user approval before pushing or creating the GitHub release.
