# self-improving-for-codex

Codex-native self-improving memory loop built around `AGENTS.md`, a durable `memories/` directory, and optional nightly maintenance automation.

## Credit

This repository started from the original work by [GODGOD126/self-improving-for-codex](https://github.com/GODGOD126/self-improving-for-codex).

The original repo established the core adaptation path:

- use `AGENTS.md` as the Codex-native entry point
- split durable memory into `PROFILE.md`, `ACTIVE.md`, `LEARNINGS.md`, `ERRORS.md`, and `FEATURE_REQUESTS.md`
- add a nightly refinement loop instead of relying on OpenClaw-only primitives

## What We Enhanced

This local branch extends the original idea into a more operational, repeatable workflow:

- promotion tagging guidance for raw memory entries:
  - `Promote To ACTIVE: none | PREF | ABS`
  - `Promotion Confidence`
  - `Promotion Notes`
- deterministic maintenance scripts:
  - `scripts/memory_sync.py`
  - `scripts/nightly_refine.py`
  - `scripts/generate_local_skill_index.py`
  - `scripts/run_night_memory_pipeline.py`
- audit logging so sync and refinement actions stay explainable
- a single-entry nightly pipeline design instead of relying on ad hoc prompt-only orchestration
- shared lock directory support via `--lock-dir`, which avoids `.maintenance.lock` conflicts across multiple Codex homes
- documentation for using a single root automation workspace so one automation run does not fan out into duplicate per-`cwd` executions

## Repository Layout

- `SKILL.md`: the skill entry and workflow
- `references/`: supporting guidance for memory files, `AGENTS.md`, and nightly review behavior
- `scripts/`: deterministic sync, refine, registry, and orchestration helpers
- `agents/openai.yaml`: Codex skill metadata

## Deterministic Scripts

### `memory_sync.py`

Conservatively syncs useful raw memory entries from an isolated bridge Codex home into the main Codex home.

### `nightly_refine.py`

Refines raw memory, updates statuses, and promotes stable candidates into `ACTIVE.md` or `PROFILE.md` when justified.

### `generate_local_skill_index.py`

Rebuilds the local skill registry for discoverability and maintenance.

### `run_night_memory_pipeline.py`

Runs the full nightly pipeline in order:

1. bridge-to-main raw memory sync
2. main memory nightly refinement
3. Sunday-only local skill index refresh

## Recommended Automation Pattern

When wiring this into Codex automations, prefer:

- one visible automation entry
- one root `cwd`
- one orchestrator script
- one shared lock directory

This avoids the common failure mode where `worktree` execution plus multiple `cwd` values turns one logical task into multiple isolated runs.

## Status

This repository now reflects both:

- the original upstream self-improving skill idea
- our local engineering enhancements for more stable real-world Codex automation
