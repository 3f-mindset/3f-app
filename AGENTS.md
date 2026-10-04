# Agent Guidance

## Work Order

Read `TODO.md` before starting implementation work. Complete the highest-priority unblocked item and update its checkbox only after its required verification passes.

For autonomous iteration, follow `ralph/PROMPT.md`. Do not begin a new TODO item until the current item is implemented, verified, documented when needed, and committed.

## Commits

Always create a Git commit after completing a cohesive change set, unless the user explicitly asks not to commit.

Use Conventional Commits for every commit message:

```text
type(scope): concise imperative summary
```

Examples:

- `feat(calibration): add furnace read slider`
- `fix(sync): preserve queued offline submissions`
- `docs: clarify local development workflow`
- `chore(deps): update locked development tools`

Use a type appropriate to the change, such as `feat`, `fix`, `docs`, `refactor`, `test`, `build`, or `chore`. Keep the summary lower-case, concise, and without a trailing period.

## Pushing

Always push the current branch to `origin` after finishing a session's work, so no commits are left local. If `origin` is not configured or the push fails, report it rather than leaving the work unpushed silently.
