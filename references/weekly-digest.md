# Weekly Digest Guidance

Use this reference when the user wants a weekly management summary for the Codex self-improving loop.

## Goal

Produce a concise operational digest that summarizes recent memory changes and checks whether the memory tiers are still healthy.

This is a read-only review workflow. It should not be the place where nightly write-side maintenance happens.

## What to read

Read in this order:

1. Tier 0: `~/.codex/memories/PROFILE.md` and `~/.codex/memories/ACTIVE.md`
2. Tier 1: `~/.codex/memories/LEARNINGS_INDEX.md` and `~/.codex/memories/ERRORS_INDEX.md`
3. Tier 2: `~/.codex/memories/LEARNINGS.md`, `~/.codex/memories/ERRORS.md`, and `~/.codex/memories/FEATURE_REQUESTS.md`
4. Tier 3 archive files only when Tier 1 and Tier 2 obviously disagree or an archive boundary needs confirmation

Mirror or bridge memory homes should only be read when freshness or divergence is itself part of the weekly review.

## What to summarize

Focus on the last 7 days:

- newly added entries
- entries whose status changed
- items promoted into `ACTIVE.md` or `PROFILE.md`
- newly recurring themes, error patterns, or feature gaps

Do not repeat the entire memory corpus.

## Health Checks

The digest should also report the health of the memory structure itself:

1. line counts and parseable entry counts for the main memory files
2. whether Tier 1 indexes appear stale relative to Tier 2 scope or topics
3. whether entry heading format is drifting, for example a mix of canonical `## [ENTRY-ID]` and legacy plain `## ENTRY-ID`
4. whether current working-set files should be compressed or rotated into archive

Suggested warning thresholds:

- `LEARNINGS.md`: around 800 lines or 60 parseable entries
- `ERRORS.md`: around 1600 lines or 100 parseable entries

These thresholds are heuristics, not hard limits. The real goal is to keep Tier 2 readable and maintainable.

## Recommended Output

Ask the weekly digest to return:

- a short grouped summary of the week
- what was promoted
- which files are bloating or drifting
- whether index refresh, archive rotation, or heading normalization is recommended next

Keep the result concise and management-friendly.
