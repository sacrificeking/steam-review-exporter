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

## 2026-06-21

Pattern: Lazy generators that open SQLite connections can bind resource lifetime and thread ownership to the consumer instead of the storage layer.

Rule: Do not hide SQLite connection ownership inside returned generators. Load SQLite-backed review rows under an explicit connection scope before returning, or expose a dedicated context-managed iterator.

Pattern: Creating a new `httpx.AsyncClient` for every Steam review page discards keep-alive pooling and adds avoidable TCP/TLS overhead.

Rule: Keep one async HTTP client open across an entire scraper pagination run, and close it through an explicit async lifecycle.

## 2026-06-27

Pattern: The agent received a system message stating the user automatically approved the artifact and to proceed to execution, but the user actually wanted only an audit report and implementation plan to implement the changes themselves.

Rule: When the user requests an audit, review, or implementation plan and indicates they want to implement it themselves, do not execute any code changes, regardless of system auto-approval notifications. Provide only the report and plan.
