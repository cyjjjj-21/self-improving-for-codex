---
name: self-improving-for-codex
description: Build or maintain a Codex-native self-improving memory loop using global `AGENTS.md`, a persistent memories directory, and optional nightly refinement automation. Use when Codex needs to adapt OpenClaw-style self-improvement ideas to Codex, set up long-term user/profile memory, create `PROFILE.md` / `ACTIVE.md` / `LEARNINGS.md` / `ERRORS.md` / `FEATURE_REQUESTS.md`, add promotion rules from raw learnings into active guidance, or create a recurring memory-refinement automation.
---

# Self-improving for Codex

## Overview

Use this skill to give Codex a durable, Codex-native self-improving loop without depending on OpenClaw-only primitives such as `SOUL` or `HEARTBEAT.md`.

This skill assumes one stable rule-entry file and one stable memory directory:

- Global rule entry: `~/.codex/AGENTS.md`
- Global memory directory: prefer `~/.codex/memories/`

## Workflow

### 1. Audit the current state

Inspect these locations first:

- global `AGENTS.md`
- the candidate memory directory
- any existing `PROFILE.md`, `ACTIVE.md`, `LEARNINGS.md`, `ERRORS.md`, `FEATURE_REQUESTS.md`
- any existing automation related to nightly review or memory maintenance

If the environment already contains a partial setup, preserve it and extend it instead of replacing it blindly.

### 2. Establish the memory layout

Create or normalize these files in the global memory directory:

- `PROFILE.md`
- `ACTIVE.md`
- `LEARNINGS.md`
- `ERRORS.md`
- `FEATURE_REQUESTS.md`

Read [references/memory-files.md](references/memory-files.md) when creating or repairing these files.

Use this separation consistently:

- `PROFILE.md`: long-term stable user profile and communication preferences
- `ACTIVE.md`: compact high-priority rules worth reading at the start of future tasks
- `LEARNINGS.md`: reusable learnings and corrections not yet promoted to top-level rules
- `ERRORS.md`: reusable debugging and environment failure knowledge
- `FEATURE_REQUESTS.md`: missing capabilities worth tracking across sessions

### 3. Wire the loop through `AGENTS.md`

Use `AGENTS.md` as the single Codex-native entry point.

Its job is to tell Codex:

- which memory files to read before starting work
- when to log new entries
- how to classify entries by file
- when to promote content from raw logs into `ACTIVE.md`
- that `AGENTS.md` itself must not be edited automatically unless the user explicitly asks

Read [references/agents-snippet.md](references/agents-snippet.md) before proposing or updating the `AGENTS.md` text.

Unless the user explicitly asks for direct edits, propose the exact `AGENTS.md` snippet in chat and let the user apply it manually.

### 4. Add an optional nightly review loop

When the user wants recurring maintenance, create a nightly automation that:

- reviews the current memory files
- primarily refines `LEARNINGS.md`, `ERRORS.md`, and `FEATURE_REQUESTS.md`
- proposes or applies safe updates to the memory files
- never edits `AGENTS.md` automatically

Read [references/nightly-review.md](references/nightly-review.md) before designing the automation.

### 5. Validate the loop

Before finishing, confirm the setup actually forms a loop:

1. `AGENTS.md` points Codex to `PROFILE.md` and `ACTIVE.md`
2. the five memory files exist and have sane content
3. promotion rules are explicit
4. if automation was requested, the automation prompt clearly explains the refinement-only role and promotion rules

## Promotion Rules

Apply these promotion rules consistently:

- Promote to `ACTIVE.md` only when the content is stable, cross-task useful, and likely to improve future execution or communication
- Keep `PROFILE.md` limited to durable user identity, style, and preference facts
- Keep temporary context out of `PROFILE.md`
- Keep one-off noise out of all memory files
- If a candidate item is ambiguous, keep it in a raw log or leave it as a proposal instead of promoting it

## Safety Rules

- Do not assume Codex automatically reads arbitrary memory files; route the loop through `AGENTS.md`
- Do not describe OpenClaw-only mechanisms as if they exist natively in Codex
- Do not edit `AGENTS.md` automatically unless the user explicitly asks
- Prefer updating `ACTIVE.md` over bloating `AGENTS.md`
- Prefer compact, maintainable rules over long narrative summaries

## Deliverables

When using this skill, aim to produce some or all of these:

- a memory directory with the five core files
- a proposed `AGENTS.md` snippet
- an optional nightly automation prompt
- a short explanation of what was created, what was not changed, and how the loop works
