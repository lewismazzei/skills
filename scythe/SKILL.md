---
name: scythe
description: Bootstrap and operate Lewis's Scythe control plane from any Codex working directory using its stable checkpoint, live Lucia worker state, and Codex usage pressure. Use when the user invokes `$scythe`, asks to start or resume Scythe, or wants the Scythe control plane/frontier.
---

# Scythe Control Plane

## Bootstrap

1. Run `python3 /home/lewis/.agents/skills/scythe/scripts/bootstrap.py` from the current directory.
2. Read `/home/lewis/projects/scythe/.codex/control-plane.md` completely. This stable file replaces numbered handoffs; never create a numbered successor.
3. Treat the script's canonical worker states and usage signal as newer than stale prose in the checkpoint. Preserve its objective, boundaries, and operator frontier.
4. Report the frontier, active exceptions, routing pressure, and exact next action tersely, then continue without asking for handoff confirmation.
5. Do not start another watcher. Lucia owns worker lifecycle, integration, deploy, push, notification, and safe cleanup.

If the checkpoint is missing or malformed, reconstruct only the stable file from durable Scythe/Lucia sources and canonical runtime records. Do not fall back to creating or continuing numbered handoffs.

## Routing

Use Standard service tier and the lowest tier that meets the evidence bar:

- Luna low/medium: clear, repeatable extraction, classification, formatting, narrow docs/config, or deterministic revalidation.
- Terra medium: normal control-plane work, bounded implementation, research synthesis, and routine workers.
- Terra high: one closeout review or a bounded difficult fix when weekly pressure is critical.
- Sol high: ambiguous architecture, security, migrations, lifecycle safety, or high-value work where Terra is demonstrably insufficient.
- Never default to `xhigh`; use it only after a measured lower-effort failure or explicit instruction.

Run deterministic checks before model calls. Allow one meaningful recovery attempt per unchanged incident and one autoreview per frozen result; rerun review only after code changes. Never run a review panel unless explicitly justified.

## Circuit breakers

- Context: `watch` at 75,000 input tokens; `rollover` at 100,000.
- Weekly allowance: compare usage consumed with elapsed share of the seven-day window. Treat above 1.25x sustainable pace as `elevated`, above 2x as `high burn`, and 95% absolute usage as `reserve`.
- In the final quarter of a window, treat pace below 0.75x as `surplus`. Prefer higher intelligence/effort on worthwhile queued work and carry a one-step increase into the next period; never generate filler work to spend quota.
- `High burn` lowers defaults and removes redundant calls but does not block useful approved work. Under `reserve`, pause discretionary model-backed work while allowing necessary recovery and customer-facing work at the lowest proven tier.
- Route clear work to Luna and normal implementation/review to Terra. Use Sol when ambiguity, quality, or safety actually requires it; current usage alone is not a prohibition.
- Tune one dimension per period—model tier or reasoning effort—and compare quality plus burn before adjusting again.
- At `rollover`, first refresh the stable checkpoint, then issue one terse notice: `Scythe checkpoint ready — open a fresh thread and invoke $scythe.` Do not create or migrate a thread yourself.

## Side effects

Normal read/write code, tests, docs, dispatch, and bounded Lucia recovery are allowed. Available manual quota resets are reserve capacity while tuning and never justify wasteful defaults. Ask before destructive cleanup, unique-work deletion, credentials/account changes, irreversible Git history, or material product-direction changes. Keep CV/profile and other private user artifacts out of product output and Git.
