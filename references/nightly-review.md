# Nightly Review Guidance

Use this reference when the user asks for a recurring review automation for the Codex self-improving loop.

## Goal

Run a nightly review that maintains the memory files without pretending Codex has OpenClaw-native memory primitives.

## What the automation should do

The nightly automation should:

1. find the real user conversation from the last 24 hours
2. review the existing memory files
3. decide what should be added, merged, promoted, or ignored
4. avoid touching `AGENTS.md`

## Where to read conversation data

Use these two layers:

1. `~/.codex/session_index.jsonl`
2. `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`

## Accurate 24-hour selection

Do not rely only on:

- folder date
- file modification time
- `updated_at` alone

Use this method:

1. compute `cutoff = local_now - 24 hours`
2. convert `cutoff` to UTC
3. parse `session_index.jsonl`
4. keep rows whose `updated_at >= cutoff_utc`
5. deduplicate by thread `id`, keeping the latest row for each id
6. locate matching `rollout-*.jsonl` files under `sessions/`
7. parse those files and extract only:
   - `type == "event_msg"`
   - `payload.type == "user_message"`
8. compare each message's own `timestamp` to `cutoff_utc`
9. treat only those kept messages as the real last-24-hours conversation set

## What to promote

Promote to `ACTIVE.md` only when content is:

- cross-task useful
- stable
- likely to improve future work
- repeated or explicitly confirmed by the user

Update `PROFILE.md` only when content is:

- a durable user preference
- a stable identity or communication fact
- clearly not temporary task context

Append to `LEARNINGS.md`, `ERRORS.md`, or `FEATURE_REQUESTS.md` when the content is valuable but not yet strong enough for top-level promotion.

## What to ignore

Do not write memory for:

- one-off chatter
- low-value noise
- fleeting context
- obvious typos
- details that do not help future sessions

## Recommended automation output

Ask the automation to output:

- the included threads
- a short Chinese summary
- proposed promotions to `ACTIVE.md`
- proposed additions to `LEARNINGS.md`, `ERRORS.md`, and `FEATURE_REQUESTS.md`
- stale or duplicate rules
- any actual file changes it made

## Safety rule

The automation may update memory files if the user wants an active maintenance loop.

It must not edit `AGENTS.md` automatically.
