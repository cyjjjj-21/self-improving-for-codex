# AGENTS Snippet Guidance

Use this reference when proposing or updating the global `AGENTS.md` integration for the Codex self-improving loop.

## Intent

`AGENTS.md` is the Codex-native rule entry point. It should:

- point Codex to the memory files
- require reading `PROFILE.md` and `ACTIVE.md` before new work
- define logging triggers
- define promotion rules
- keep `AGENTS.md` itself under manual user control

## Recommended Rule Shape

Keep the `Self-Improvement` section explicit and operational.

It should define:

1. memory directory location
2. startup reads
3. logging triggers
4. file-by-file routing
5. promotion rules
6. the boundary between `ACTIVE.md` promotion and `AGENTS.md` promotion

## Recommended Text

```md
## Self-Improvement

Use the global memory directory at `C:\Users\Administrator\.codex\memories`.

Before starting any task:
1. Read `C:\Users\Administrator\.codex\memories\PROFILE.md`
2. Read `C:\Users\Administrator\.codex\memories\ACTIVE.md`
3. Apply them as global memory before analyzing the user request

Log only when the outcome is non-obvious, reusable, or likely to recur.

Evaluate whether to log a memory entry when any of the following happens:
1. A command, tool call, or operation fails unexpectedly
2. The user corrects a mistake, assumption, or outdated statement
3. A requested capability does not exist yet
4. An external API, integration, or tool behaves differently than expected
5. A non-obvious workaround, debugging insight, or better recurring approach is discovered

Write entries by type:
- `C:\Users\Administrator\.codex\memories\LEARNINGS.md` for learnings, corrections, knowledge gaps, and best practices
- `C:\Users\Administrator\.codex\memories\ERRORS.md` for unexpected errors and debugging notes
- `C:\Users\Administrator\.codex\memories\FEATURE_REQUESTS.md` for missing capabilities the user wants

Promotion rules:
1. If a pattern recurs or is broadly useful across tasks, promote it into `C:\Users\Administrator\.codex\memories\ACTIVE.md`
2. Keep `ACTIVE.md` concise and current
3. Only promote something into this `AGENTS.md` when it becomes a stable top-level rule, or when the user explicitly asks

Behavior expectations:
- Default to Chinese when writing memory entries unless the user asks otherwise
- Do not interrupt the user for every possible learning; log silently when confidence is high
- Do not log trivial typos, one-off noise, or low-value observations
```

## Adaptation Notes

- Replace paths when the user's Codex home differs
- If the user already has a good `Self-Improvement` section, extend it instead of replacing it blindly
- If the user wants project-local memory instead of global memory, make that change explicit and explain the tradeoff
