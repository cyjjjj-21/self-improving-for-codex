# Nightly Review Guidance

Use this reference when the user asks for a recurring review automation for the Codex self-improving loop.

## Goal

Run a nightly refinement pass that maintains the memory files without pretending Codex has OpenClaw-native memory primitives.

## What the automation should do

The nightly automation should:

1. read the existing memory files
2. focus on `LEARNINGS.md`, `ERRORS.md`, and `FEATURE_REQUESTS.md`
3. refine, merge, deduplicate, and promote stable items
4. update `ACTIVE.md` or `PROFILE.md` only when promotion is justified
5. avoid touching `AGENTS.md`

This automation is not the primary place to harvest raw learnings from conversation replay. The intended loop is:

- daytime task flow logs worthwhile items into raw memory files
- nightly automation refines those raw memory files into cleaner top-level guidance

## What to read

Read these files:

1. `~/.codex/memories/PROFILE.md`
2. `~/.codex/memories/ACTIVE.md`
3. `~/.codex/memories/LEARNINGS.md`
4. `~/.codex/memories/ERRORS.md`
5. `~/.codex/memories/FEATURE_REQUESTS.md`

Prioritize `LEARNINGS.md`, `ERRORS.md`, and `FEATURE_REQUESTS.md` as the source material for refinement.

## Refinement scope

The current preferred behavior is:

- review the raw memory logs
- focus especially on additions from the recent period, such as the last 24 hours of newly logged items
- decide which items should stay as raw history
- decide which items should be merged, rewritten, or marked stale
- decide which stable items now deserve promotion into `ACTIVE.md` or `PROFILE.md`

Do not reconstruct the day from raw conversation transcripts unless the user explicitly asks for that broader recovery workflow.

## What to promote

Promote to `ACTIVE.md` only when content is:

- cross-task useful
- stable
- likely to improve future work
- repeated or explicitly confirmed by the user

Promote to `PROFILE.md` only when content is:

- a durable user preference
- a stable identity or communication fact
- clearly not temporary task context

Keep items in `LEARNINGS.md`, `ERRORS.md`, or `FEATURE_REQUESTS.md` when they are valuable but not yet strong enough for top-level promotion.

## What to clean up

The automation may:

- merge duplicates
- tighten unclear wording
- update stale statuses
- remove overlap between near-identical entries

It should not over-prune raw evidence. Preserve enough history to keep later decisions explainable.

## What to ignore

Do not promote:

- one-off chatter
- low-value noise
- fleeting context
- obvious typos
- details that do not help future sessions

## Recommended automation output

Ask the automation to output:

- which memory files it read
- which files it changed and why
- what it promoted into `ACTIVE.md` or `PROFILE.md`
- what it merged, rewrote, or left untouched
- which candidate items it refused to promote and why
- which stale or duplicate entries still need cleanup

## Recommended Prompt Text

Use this prompt as the current recommended baseline when creating the nightly refinement automation:

```text
这是 Codex 全局 self-improving 体系的夜间精炼任务。你的目标不是回看当天全部对话，而是维护 `C:\Users\Administrator\.codex\memories` 下已经沉淀出的记忆文件，让 Codex 后续回答更贴合用户、更稳定。先理解文件分工：`PROFILE.md` 只存长期稳定的用户画像与沟通偏好；`ACTIVE.md` 只存高优先级、跨任务有效、每次新任务都值得先看的规则；`LEARNINGS.md` 记录非显而易见、可复用、可能再次出现的经验、纠正、知识更新和最佳实践；`ERRORS.md` 记录非显而易见、值得复用、未来可能再次出现的错误与排障经验；`FEATURE_REQUESTS.md` 记录用户提出但当前能力或闭环尚未完全满足、值得长期跟踪的需求。这个自动化只负责精炼、去重、合并、升级，不负责从原始对话回放中补记 learnings。默认假设白天对话过程中，值得记录的内容已经按规则写入了 `LEARNINGS.md`、`ERRORS.md`、`FEATURE_REQUESTS.md`。你的核心任务是读取 `LEARNINGS.md`、`ERRORS.md`、`FEATURE_REQUESTS.md`，并从过去24小时的新增内容中，判断其中哪些内容已经足够稳定，应该提升到 `ACTIVE.md` 或 `PROFILE.md`；同时清理重复、互相重叠或表达不清的条目。提炼规则必须严格执行：只有非显而易见、可复用、可能再次出现、跨任务有效、或能明显提升后续沟通质量、执行质量、排障效率的内容，才值得保留或升级；一次性任务细节、纯闲聊、纯情绪表达、临时上下文、显而易见的小失误、没有复用价值的噪音，不要提升到顶层记忆。升级到 `PROFILE.md` 的条件是：它属于长期稳定的用户画像、沟通方式、技术背景、工作偏好，而且明显不是临时要求。升级到 `ACTIVE.md` 的条件是：它已足够稳定、跨任务有效、应在未来每次任务开始前优先参考；尤其当同类内容在原始日志中多次出现，或用户明确表达“以后都按这个来”“这是长期规则”“这个要记住”时，应优先考虑提升。`ACTIVE.md` 必须保持精简；发现重复规则时要合并，发现过时或被上位规则覆盖的条目时要删除或改写。`PROFILE.md` 也只保留长期稳定事实，不要塞入临时偏好。`LEARNINGS.md`、`ERRORS.md`、`FEATURE_REQUESTS.md` 中如果存在明显重复、状态过时、描述不清，也可以在不改变原意的前提下做整理，但不要把原始证据删得过度，避免失去追溯价值。执行策略要保守：如果你对某条内容是否值得升级没有足够把握，就不要直接改 `PROFILE.md` 或 `ACTIVE.md`；如果本轮没有足够高价值的升级内容，就允许只输出复盘摘要而不修改任何记忆文件。输出必须是中文，并且必须包含：本次读取了哪些记忆文件；你实际修改了哪些记忆文件以及为什么；你新增、合并、改写或删除了哪些规则；哪些内容被提炼进了 `ACTIVE.md` 或 `PROFILE.md` 以及提炼理由；哪些候选内容被你放弃升级以及放弃理由；还有哪些重复、过时或低质量条目需要后续清理。绝对不要自动修改 `AGENTS.md`；如果你认为某条内容已经值得进入 `AGENTS.md`，只能在输出里给出建议文本，不得直接写入。
```

## Safety rule

The automation may update memory files if the user wants an active maintenance loop.

It must not edit `AGENTS.md` automatically.
