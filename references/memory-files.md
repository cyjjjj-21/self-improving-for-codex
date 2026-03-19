# Memory Files Guidance

Use this reference when creating or repairing the memory directory for the Codex self-improving loop.

## Core Files

Create these files:

- `PROFILE.md`
- `ACTIVE.md`
- `LEARNINGS.md`
- `ERRORS.md`
- `FEATURE_REQUESTS.md`

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

### `ERRORS.md`

Use for:

- environment-specific failures
- reusable debugging patterns
- subtle command/tool gotchas

### `FEATURE_REQUESTS.md`

Use for:

- long-term missing capabilities
- gaps in the current Codex workflow
- repeated user asks that are not fully solved

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

## [LRN-YYYYMMDD-001] category
**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending | resolved | promoted | wont_fix

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

## [ERR-YYYYMMDD-001] command_or_tool
**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending | resolved | promoted | wont_fix

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

## [FEAT-YYYYMMDD-001] capability_name
**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending | resolved | promoted | wont_fix

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
- only promote stable user identity and preference facts to `PROFILE.md`
- keep uncertain items in raw logs until they recur or the user confirms them
