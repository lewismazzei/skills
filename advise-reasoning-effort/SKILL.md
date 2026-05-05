---
name: advise-reasoning-effort
description: Suggests the appropriate Codex reasoning effort before substantial work starts. Use proactively for GPT-5.5/Codex tasks where low, medium, high, or xhigh choice materially affects autonomy, quality, latency, or cost; stay silent for trivial tasks or when the default is clearly fine.
---

# Reasoning Effort Advisor

Recommend the Codex reasoning effort for the task at hand before substantive work begins. This skill is advisory only: do not stop the thread, do not ask the user to switch settings by default, and do not reduce autonomy.

## Baseline

For GPT-5.5, assume the user's baseline is `medium`.

Stay silent when `medium` is the right setting. Speak up only when another setting is meaningfully better, or when the task is expensive enough that the choice deserves an explicit note.

The agent usually cannot reliably inspect the current thread's effective setting. Phrase advice as conditional: "Use `high` if you are not already there."

## Recommendation Rubric

Use `low` when speed and cost matter more than peak quality, and the work is straightforward:

- Small edits, obvious fixes, mechanical refactors, formatting, docs cleanup, simple scripts.
- Execution-heavy coding where the task is clear and the codebase area is familiar.
- Quick search, summarization, drafting, or low-risk data analysis.
- Follow-up turns after the plan and hard decisions are already settled.

Use `medium` as the default:

- Most agentic coding, research, spreadsheet/slides/doc work, and multi-step tasks.
- Moderate planning, codebase navigation, tool use, judgment, or synthesis.
- Work where quality matters but the failure cost is ordinary.
- Any task that does not clearly justify `low`, `high`, or `xhigh`.

Use `high` when quality and judgment matter more than latency:

- Hard debugging, ambiguous regressions, architecture/design decisions, migrations, incident analysis.
- Larger code changes with cross-module behavior, shared contracts, data migrations, or high blast radius.
- Long-horizon research or technical planning where missing a dependency would be costly.
- Code review where subtle correctness, security, or maintainability risks matter.

Use `xhigh` only for the hardest or longest work:

- Deep security review, high-stakes code review, or adversarial analysis.
- Very hard bugs where lower efforts have failed or the cause is deeply hidden.
- Broad architecture changes, complex migrations, or repo-wide refactors with many interacting constraints.
- Long asynchronous agentic tasks, multi-agent orchestration, or deep research where extra latency and cost are acceptable.

## Proactive Advice Format

Keep the advice to one short sentence before starting work:

`Reasoning effort: use high if you are not already there; this touches shared auth flow and needs careful regression analysis.`

Do not repeat the recommendation in later updates unless the task changes meaningfully.

## Escalation And De-escalation

Escalate from `medium` to `high` or `xhigh` when the task reveals hidden complexity, failed attempts, weak test seams, or high-risk side effects.

De-escalate to `low` when the next turn is mostly mechanical execution after the hard reasoning is complete.

If the user explicitly names a setting, respect it and continue.
