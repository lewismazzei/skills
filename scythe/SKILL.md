---
name: scythe
description: Bootstrap and operate Lewis's Scythe control plane from any Codex working directory using its durable checkpoint, live Lucia worker state, and Codex usage pressure. Use for $scythe and for the exact keywords "nudge" and "retro" in a Scythe ingress or controller thread.
---

# Scythe Control Plane

## Bootstrap

1. Classify the operator request before doing anything else. For an ordinary `status` request or exact `retro`, run `python3 /home/lewis/.agents/skills/scythe/scripts/bootstrap.py --request status`. For `$scythe`, exact `nudge`, `continue`, or another acting request, run the same command with `--request continue`.
2. Read `/home/lewis/projects/scythe/.codex/control-plane.md` completely as the durable control-plane checkpoint.
3. Check `checkpoint.status`. If it is not `healthy`, reconcile the checkpoint to the current-state contract below before relying on it or giving a final response.
4. Treat the script's canonical controller, worker, watcher, and usage state as newer than checkpoint prose. Preserve the objective, boundaries, and real operator frontier while removing superseded claims.
5. Check `controller.authority` before acting. Continue when it is `active` or `unregistered`. If it is `pending`, `handoff-in-progress`, `superseded`, or `invalid-registry`, do not edit or dispatch; report the active controller name, thread id, and deep link.
6. Report the frontier, active exceptions, routing pressure, and exact next action tersely, then take any immediate non-overlapping control-plane action without asking for handoff confirmation.
7. Do not start another watcher. Lucia owns worker lifecycle, integration, deploy, push, notification, and safe cleanup.
8. When the next action is Lucia-owned and asynchronous, return control to the user immediately after reconciliation or durable worker guidance. Do not poll, wait, or keep the turn open for worker completion, integration, deploy, or cleanup unless the user explicitly asks to monitor or block.

If the checkpoint is missing or malformed, reconstruct it from durable Scythe/Lucia sources and canonical runtime records.

## Read-only status

- An ordinary `status`, exact `retro`, “what is happening?”, or equivalent observation request is a strict read-only operation. Read the bootstrap report, checkpoint, Git refs, release manifests, worker records, and service state; then report them.
- During read-only status, do not edit files, update the checkpoint or controller registry, enqueue ingress, dispatch or recover workers, run Lucia with `--apply`, restart services, trigger a release, push, or request compaction.
- Surface recoverable faults and the exact next acting operation, but leave both untouched. Only `$scythe`, exact `nudge`, `continue`, or an explicit change/recovery request authorizes the act-before-final workflow.
- The bootstrap itself is read-only for every request. Its `continuation.mutations_allowed` field is the machine-readable authority boundary.

## Retro keyword

- Treat an operator message whose command is exact `retro` in a Scythe ingress or controller thread as a read-only retrospective request.
- Start the period at the most recent preceding human-authored message. End it when `retro` starts. State both boundaries. Automated Lucia ingress messages are evidence inside the period and never reset its start. This includes watcher-delivered `Run $scythe for this operator message:` messages, `Lucia ...` lifecycle messages, and structured `continuation:` payloads.
- Reconstruct the period from the thread and canonical durable records. Distinguish user actions, controller actions, Lucia actions, worker actions, and periods with no frontier change.
- Report the intended outcome, material releases or retained work, faults and retries, idle or stuck intervals, usage or pacing effect, present consequence, and the main lesson. Do not count repeated observations as progress.
- If a service is active but the frontier does not change, report the frontier as stalled. State the last material change and elapsed idle time.
- `retro` must not edit files, update the checkpoint, dispatch or recover workers, acknowledge continuations, release, push, restart services, or otherwise advance the frontier. Use exact `nudge` for status plus action.

## Nudge keyword

- Treat an operator message whose command is exact `nudge` in a Scythe ingress or controller thread as an acting request.
- `nudge` means: inspect the canonical live state, execute each safe immediate non-overlapping action that is needed, repair recoverable control-plane faults, persist the current frontier, and explain why action was needed.
- Return control when no safe synchronous action remains or Lucia owns a confirmed asynchronous next action.
- `nudge` does not mean monitor or wait, bypass authority or pacing gates, create a goal, start duplicate work, or make ordinary `status` action-bearing.

## Checkpoint contract

`control-plane.md` is a compact current-state index, not an event log, worker diary, or transcript summary.

- Keep only these level-two sections, in order: `Objective`, `Frontier`, `Active lifecycle`, `Active exceptions`, `Exact next actions`, `Boundaries`, and `Durable sources`.
- Keep the file below 16 KiB. Treat bootstrap `checkpoint.status != healthy` as a control-plane incident to repair in the foreground.
- Keep exactly one authoritative-controller claim and make it match bootstrap. Number exact next actions contiguously from 1.
- Remove completed worker narratives, predecessor-controller state, superseded incidents, old deploy attempts, and `[Verified, historical]` entries. Collapse useful completion evidence into one current frontier sentence or point to its durable Git, Lucia, ADR, production-status, or worker record.
- Do not copy canonical worker inventories into prose. Record only workers that own a current next action or active exception; bootstrap remains the live inventory.
- Update in place after every material frontier change. Never append a new lifecycle chronicle to the bottom.

## Continue act-before-final gate

- Apply this section only to `$scythe`, exact `nudge`, `continue`, or another acting request. Treat the bootstrap `continuation` object as a final-response gate. For an `active` or `unregistered` controller in acting mode, `status_only_allowed` is false.
- Do not apply this section to exact `retro`. `retro` is always read-only.
- Before answering an acting request, enumerate the checkpoint's exact next actions and execute every safe immediate non-overlapping action available in the foreground.
- Do not report a recoverable control-plane fault as the terminal outcome. Diagnose and repair Scythe/Lucia orchestration faults directly, then resume the product frontier.
- A worker marked `blocked`, a stale verifier, a dirty-source guard, an eligibility mismatch, or a stopped watcher is an incident to reconcile, not automatically a reason to stop.
- Before the final response, satisfy the machine-readable `required_before_final` list: execute safe immediate actions, repair recoverable control-plane faults, confirm any asynchronous owner is genuinely advancing, and persist the updated frontier.
- When `required_before_final` contains `reconcile-checkpoint-hygiene`, compact the checkpoint to the contract above and rerun bootstrap before finishing.
- Stop only at one of the bootstrap `stop_only_when` conditions: no safe synchronous action remains; Lucia owns a confirmed asynchronous next action; or authority, approval, credential, destructive, or product-direction boundaries prevent continuation.
- If the user explicitly asks for a read-only audit or forbids changes, preserve that narrower authority and report what action would otherwise have been taken.

## Worker launch invariant

- Initiate every delegated worker through Lucia's background `codex exec` path: `node /home/lewis/projects/lucia/lucia.mjs spawn --background --task ... --owner ... --avoid ...`.
- Before each model-backed spawn, recovery, or review, rerun bootstrap. Require `pressure.weekly_pacing_guard == "open"` and `pressure.discretionary_model_work_allowed == true` for discretionary work. When the guard is closed, start only necessary recovery or customer-facing release work at the lowest proven tier.
- Keep at most one active model-backed worker. Start the next worker only after the current worker reaches a terminal handoff state.
- Never use native `spawn_agent`, collaboration subagents, or another controller-child thread mechanism for Scythe work. Worker threads must be independent top-level threads so controller rollover and later archival cannot interrupt them.
- After launch, treat the persisted Codex thread id as authoritative. When app-server relationship metadata is available, require `parentThreadId` to be null. A non-null parent is a lifecycle violation: stop dispatching further work, preserve the worker state/worktree, and route repair through Lucia rather than archiving the controller.
- Controller-local reconciliation, deterministic inspection, checkpoint maintenance, and routing decisions are not delegated worker work and remain in the foreground thread.

## Routing

Use Standard service tier and the lowest tier that meets the evidence bar:

- Sol xhigh: default for Scythe control-plane threads, by explicit operator choice.
- Luna low/medium: clear, repeatable extraction, classification, formatting, narrow docs/config, or deterministic revalidation.
- Terra medium: bounded implementation, research synthesis, and routine workers.
- Terra high: one closeout review or a bounded difficult fix when weekly pressure is critical.
- Sol high: difficult architecture or lifecycle decisions, security, migrations, or high-value ambiguity.
- Keep `xhigh` scoped to controller threads. Workers still use the lowest tier and effort that meet their evidence bar.

Run deterministic checks before model calls. Allow one meaningful recovery attempt per unchanged incident and one autoreview per frozen result; rerun review only after code changes. Never run a review panel unless explicitly justified.

## Circuit breakers

- Context: `watch` at 125,000 input tokens; expect native compaction at 150,000 while retaining the same authoritative thread.
- Weekly pacing guard: allow a 5 percentage-point startup burst, then grow the spend limit with 90% of elapsed weekly time, capped at 95%. This preserves a 5-point end reserve. Never assume that a manual reset is available.
- Weekly allowance: compare usage consumed with elapsed share of the seven-day window. Treat above 1.25x sustainable pace as `elevated`, above 2x as `high burn`, and 95% absolute usage as `reserve`.
- In the final quarter of a window, treat pace below 0.75x as `surplus`. Prefer higher intelligence/effort on worthwhile queued work and carry a one-step increase into the next period; never generate filler work to spend quota.
- `High burn` lowers defaults and removes redundant calls but does not block useful approved work. Under `reserve`, pause discretionary model-backed work while allowing necessary recovery and customer-facing work at the lowest proven tier.
- Route clear work to Luna and normal implementation/review to Terra. Use Sol when ambiguity, quality, or safety actually requires it; current usage alone is not a prohibition.
- Tune one dimension per period—model tier or reasoning effort—and compare quality plus burn before adjusting again.
- Never create a successor controller merely because context is large. Keep one permanent authoritative thread and let Codex's native compaction preserve the active goal and current conversation.
- The legacy `rollover.py` CLI is compatibility-safe: every invocation requests compaction of the current thread and cannot create a successor. Do not invoke it during ordinary work; native compaction is automatic.
- If native compaction genuinely fails and the current thread cannot proceed, persist the checkpoint and report an authority boundary. Do not revive routine controller switching.

## Side effects

Normal read/write code, tests, docs, dispatch, and bounded Lucia recovery are allowed. Available manual quota resets are reserve capacity while tuning and never justify wasteful defaults. Ask before destructive cleanup, unique-work deletion, credentials/account changes, irreversible Git history, or material product-direction changes. Keep CV/profile and other private user artifacts out of product output and Git.
