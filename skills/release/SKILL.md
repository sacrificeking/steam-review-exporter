# Release Skill

Use this skill for commits, tags, GitHub releases, release notes, or publishing.

## Preconditions

1. Run `git status -sb`.
2. Confirm the intended scope.
3. Select the next version using Semantic Versioning.
4. Create release notes for that exact version.
5. Run fast verification.
6. Ensure release notes match the shipped behavior.

## Semantic Versioning

- Patch: backward-compatible bug fixes, robustness work, documentation fixes, and internal hardening.
- Minor: backward-compatible features or user-facing capability additions.
- Major: breaking changes to CLI behavior, library APIs, file formats, or supported runtime expectations.

Use tags in the form `vMAJOR.MINOR.PATCH`.

## Commit Checklist

1. Stage only intended files.
2. Commit with a concise message.
3. Re-check `git status -sb`.

## Tag Checklist

1. Use semantic version tags such as `v1.0.0`.
2. Prefer annotated tags for releases.
3. Do not push the tag until the user explicitly approves publishing in the current turn.

## GitHub Release Checklist

1. Create or update release notes.
2. Create the GitHub release from the tag.
3. Verify release URL.
4. Verify CI status.

## Safety Rules

- Do not publish secrets or local artifacts.
- Do not delete remote tags or releases without explicit user approval.
- Do not run `git push`, create/update GitHub releases, or otherwise modify GitHub remote state without explicit user approval in the current turn.
- If auth or permissions fail, stop and report the exact blocker.
