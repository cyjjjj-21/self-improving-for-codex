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
- launchd-oriented wrappers and status files for write-side nightly maintenance outside Codex `worktree` sandboxes
- a split nightly pattern where launchd performs real writes and a later Codex automation only reads precomputed summary artifacts to open an inbox item
- a progressive-disclosure memory layout where startup reads stay on `PROFILE.md` + `ACTIVE.md`, index files guide deeper lookup, and older raw memory can move into archive files without losing traceability
- compatibility parsing for both canonical `## [ENTRY-ID] title` headings and legacy plain `## ENTRY-ID` headings in raw memory files
- explicit working-set health guidance so large `LEARNINGS.md` / `ERRORS.md` files trigger index refresh, archive rotation, or compression instead of silent bloat
- weekly digest guidance that audits recent memory changes plus the health of the memory tiers themselves

## Repository Layout

- `SKILL.md`: the skill entry and workflow
- `references/`: supporting guidance for memory files, `AGENTS.md`, and nightly review behavior
- `references/weekly-digest.md`: guidance for optional weekly management summaries
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

The current pipeline is fail-fast:

- if bridge sync fails, refinement and weekly index refresh are marked `skipped`
- if refinement fails, weekly index refresh is also marked `skipped`
- optional `--status-path` writes a machine-readable JSON payload with step status and timestamps

This pipeline intentionally does not create a visible weekly management digest. Treat that as a separate read-only automation so nightly write-side maintenance stays predictable.

### `launchd_night_memory_pipeline.py`

Wrapper intended for macOS `launchd` execution:

- publishes an initial `running` status
- invokes `run_night_memory_pipeline.py --apply`
- generates the final nightly summary for the same `run_id`
- updates the canonical status file with `summary_status`, `summary_ready`, and summary metadata

### `launchd_night_memory_summary.py`

Companion summary generator intended for isolated summary homes:

- runs `codex exec` from a lightweight dedicated `CODEX_HOME`
- preserves raw stderr/stdout logs plus a filtered human-readable stderr log
- returns non-zero when it degrades to fallback mode
- validates `run_id` so stale summaries are not mistaken for the current nightly run

## Recommended Automation Pattern

When wiring this into Codex automations and macOS scheduling, prefer:

- one `launchd` job at `01:30` for the write-side pipeline
- one canonical status file such as `~/.codex/runtime/night-memory-pipeline/last_run.json`
- one precomputed summary artifact such as `~/.codex/runtime/night-memory-summary/last_summary.txt`
- one visible Codex automation at `02:00` that only reads those artifacts and opens an inbox item
- one optional weekly digest automation that reviews the last 7 days of memory changes and checks whether indexes, heading formats, and working-set size are drifting
- one root `cwd`

This avoids the common failure mode where `worktree` execution plus multiple `cwd` values turns one logical task into multiple isolated runs, and it also prevents write-side permission failures inside automation sandboxes.

## Launchd Example

See:

- `examples/launchd/com.example.codex.night-memory-pipeline.plist.example`

Use placeholders instead of hardcoded local usernames or home paths when adapting the example.

## Status

This repository now reflects both:

- the original upstream self-improving skill idea
- our local engineering enhancements for more stable real-world Codex automation
