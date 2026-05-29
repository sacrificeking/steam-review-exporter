# Release Skill

Use this skill for commits, tags, GitHub releases, release notes, or publishing.

## Preconditions

1. Run `git status -sb`.
2. Confirm the intended scope.
3. Run fast verification.
4. Ensure release notes match the shipped behavior.

## Commit Checklist

1. Stage only intended files.
2. Commit with a concise message.
3. Re-check `git status -sb`.

## Tag Checklist

1. Use semantic version tags such as `v1.0.0`.
2. Prefer annotated tags for releases.
3. Push branch and tag intentionally.

## GitHub Release Checklist

1. Create or update release notes.
2. Create the GitHub release from the tag.
3. Verify release URL.
4. Verify CI status.

## Safety Rules

- Do not publish secrets or local artifacts.
- Do not delete remote tags or releases without explicit user approval.
- If auth or permissions fail, stop and report the exact blocker.
