# Memory Files Guidance

Use this reference when creating or repairing the memory directory for the Codex self-improving loop.

## Core Files

Create these files:

- `PROFILE.md`
- `ACTIVE.md`
- `LEARNINGS.md`
- `ERRORS.md`
- `FEATURE_REQUESTS.md`

Optional support files when the raw logs get large:

- `LEARNINGS_INDEX.md`
- `ERRORS_INDEX.md`
- `archive/README.md`
- one or more archive files under `archive/`, for example `LEARNINGS_2026_Q1.md`

## Role of Each File

### `PROFILE.md`

Use for:

- stable user role
- technical level
- stable communication preferences
- durable working preferences

Do not use for:

- temporary tasks
- one-off instructions
- short-lived project context

### `ACTIVE.md`

Use for:

- high-priority rules worth reading before most tasks
- promoted content from repeated or important learnings

Keep it:

- short
- current
- deduplicated

### `LEARNINGS.md`

Use for:

- reusable lessons
- user corrections
- knowledge updates
- best practices not yet promoted

If this file gets heavy:

- keep only the current working set in `LEARNINGS.md`
- move older settled items into archive files
- summarize buckets and retrieval hints in `LEARNINGS_INDEX.md`

### `ERRORS.md`

Use for:

- environment-specific failures
- reusable debugging patterns
- subtle command/tool gotchas

If this file gets heavy:

- keep only the current working set in `ERRORS.md`
- move older settled items into archive files
- summarize buckets and retrieval hints in `ERRORS_INDEX.md`

### `FEATURE_REQUESTS.md`

Use for:

- long-term missing capabilities
- gaps in the current Codex workflow
- repeated user asks that are not fully solved

## Progressive Disclosure Pattern

When the memory corpus starts getting heavy, prefer this read order:

1. `PROFILE.md`
2. `ACTIVE.md`
3. `LEARNINGS_INDEX.md` / `ERRORS_INDEX.md` only when deeper lookup is needed
4. `LEARNINGS.md` / `ERRORS.md` only when the index points to a relevant current bucket
5. `archive/` only when current raw files are insufficient

This keeps startup memory light while preserving explainable history.

## Suggested Minimal Templates

### `PROFILE.md`

```md
# PROFILE

## User Role
- ...

## Technical Level
- ...

## Communication Preferences
- ...

## Working Preferences
- ...

## Last Updated
- YYYY-MM-DD
```

### `ACTIVE.md`

```md
# ACTIVE

## Always Apply
- [ACT-001] ...
  Source: ...

## Maintenance Rules
- Keep this file concise

## Last Reviewed
- YYYY-MM-DD
```

### `LEARNINGS.md`

```md
# LEARNINGS

## Promotion Tagging Standard

- `Promote To ACTIVE`: `none` | `PREF` | `ABS`
- `Promotion Confidence`: `low` | `medium` | `high`
- `Promotion Notes`: short reason for the current classification

## [LRN-YYYYMMDD-001] category
**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending | resolved | promoted | wont_fix
**Promote To ACTIVE**: none | PREF | ABS
**Promotion Confidence**: low | medium | high
**Promotion Notes**: ...

### Summary
...

### Details
...

### Suggested Action
...

### Metadata
- Source: conversation | error | user_feedback
- Tags: ...
```

### `ERRORS.md`

```md
# ERRORS

## Promotion Tagging Standard

- `Promote To ACTIVE`: `none` | `PREF` | `ABS`
- `Promotion Confidence`: `low` | `medium` | `high`
- `Promotion Notes`: short reason for the current classification

## [ERR-YYYYMMDD-001] command_or_tool
**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending | resolved | promoted | wont_fix
**Promote To ACTIVE**: none | PREF | ABS
**Promotion Confidence**: low | medium | high
**Promotion Notes**: ...

### Summary
...

### Error
```text
...
```

### Context
- Command: ...
- Situation: ...
- Environment: ...

### Suggested Fix
...
```

### `FEATURE_REQUESTS.md`

```md
# FEATURE_REQUESTS

## Promotion Tagging Standard

- `Promote To ACTIVE`: `none` | `PREF` | `ABS`
- `Promotion Confidence`: `low` | `medium` | `high`
- `Promotion Notes`: short reason for the current classification

## [FEAT-YYYYMMDD-001] capability_name
**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending | resolved | promoted | wont_fix
**Promote To ACTIVE**: none | PREF | ABS
**Promotion Confidence**: low | medium | high
**Promotion Notes**: ...

### Requested Capability
...

### User Context
...

### Suggested Implementation
...
```

## Promotion Rules

Use these default rules:

- only promote stable cross-task knowledge to `ACTIVE.md`
- use `ABS` inside `ACTIVE.md` for near-non-negotiable collaboration rules
- use `PREF` inside `ACTIVE.md` for stable but overridable communication or delivery preferences
- only promote stable user identity and preference facts to `PROFILE.md`
- keep uncertain items in raw logs until they recur or the user confirms them
