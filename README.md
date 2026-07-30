# Agent Skills

Personal agent skills for AI coding agents.

## Local workflow

This repository is the source of truth for personal skills only. The active
global Codex install lives outside this repo:

- `~/skills`: personal skill source repo, committed and pushed to GitHub.
- `~/.agents/skills`: real global install directory used by `npx skills`.
- `~/.codex/skills`: Codex directory; user skill entries are symlinks to
  `~/.agents/skills`, while Codex-managed `.system` skills remain here.

Install or update a pushed skill into the global Codex install:

```bash
add-skill lewismazzei/skills/<skill-name> -y
```

Test local repo edits before pushing:

```bash
npx skills add ./<skill-name> -g -a codex -y
```

Refresh Codex symlinks after a manual install:

```bash
sync-skills-links
```

Audit skill source/install/runtime drift:

```bash
~/skills/manage-personal-skills/scripts/audit-skills.sh
```

## Golden flow

Use the `manage-personal-skills` skill before changing skill installs, source
skills, or Codex runtime links.

Before changes:

```bash
~/skills/manage-personal-skills/scripts/audit-skills.sh
```

For personal skills:

- Edit only this repo first.
- Keep the skill directory name and `SKILL.md` frontmatter `name` in sync.
- Update this `README.md` in the same change.
- Commit and push the source repo before treating it as the new source of truth.
- Install or refresh the active global copy from the pushed repo.
- Ensure `~/.codex/skills/<skill-name>` is a symlink to `../../.agents/skills/<skill-name>`.

For third-party skills:

- Install into the global runtime, not this repo.
- Keep third-party skill files out of `~/skills`.
- Ensure the `.codex` entry is a symlink into `.agents`.

After changes:

```bash
~/skills/manage-personal-skills/scripts/audit-skills.sh
```

Resolve all `ERROR` lines before committing. Prefer separate commits for
separate intents: obsolete removals, personal skill additions or renames,
executable sync fixes, and third-party install normalization.

## dispatch

Dispatch coding or research work to pet-named background worker agents in
dedicated Git worktrees while the parent thread remains the control plane.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/dispatch -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/dispatch -g -a codex -y
```

Typical uses:

- Use `/dispatch <task>` to create a worker worktree, launch an independent top-level `codex exec` worker, and immediately return control to the parent thread.
- Never use native controller-child subagents for dispatched work; require a null `parentThreadId` when relationship metadata is available so controller archival cannot terminate workers.
- Store default worker checkouts under `<repo-parent>/.worktrees/<repo-name>/<worker>`; for repos in `/home/lewis/projects`, this keeps project worktrees grouped under `/home/lewis/projects/.worktrees/<project>/`.
- Track workers by short pet names such as `bright-lantern`.
- On a pet-name collision, allocate a completely new adjective-noun pair; never append a number.
- Use `<project-slug>/worker/<pet-name>` as the display name when the thread surface exposes naming, while keeping the short pet name as the durable worker id.
- Queue parent-to-worker guidance through disk-backed inbox files.
- Poll worker status with a cron-safe watcher that queues parent notifications.
- Require ready workers to satisfy a SwarmForge-inspired verification
  constitution: acceptance contract, red evidence, scoped implementation,
  cleanup/architecture review, hardening gates, and QA handoff proof.
- Require proof for the original user-visible symptom, including
  production/default configuration paths for optional integrations.
- Ask before destructive cleanup and refuse cleanup for dirty worktrees or unmerged branches.

## explore-prototype

Build implementation-ready specifications from prototype URLs using Playwright exploration plus source extraction.

Install globally for Codex:

```bash
npx skills add https://github.com/lewismazzei/skills --skill explore-prototype -g -a codex
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/explore-prototype -g -a codex
```

Typical uses:

- Analyze a prototype URL into `spec.md`, `analysis.json`, and screenshots.
- Capture hidden modals, data models, formulas, and AI response maps.
- Run discovery-only mode before deep analysis.

## guide-handoff-prompt

Create, revise, or review handoff scripts and prompts for another AI agent or OpenAI model using current OpenAI prompt guidance.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/guide-handoff-prompt -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/guide-handoff-prompt -g -a codex -y
```

Typical uses:

- Invoke explicitly with `$guide-handoff-prompt`; Codex does not select it implicitly.
- Write model-specific handoff prompts, subagent prompts, or runbook prompts.
- Check that a handoff has success criteria, stopping rules, allowed side effects, and output expectations.
- Align prompt guidance with current OpenAI developer docs before delivery.

## handoff-session

Create or update a living handoff for a multi-thread work session.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/handoff-session -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/handoff-session -g -a codex -y
```

Typical uses:

- Invoke explicitly with `$handoff-session`; Codex does not select it implicitly.
- Preserve the current state frontier before ending or crossing a thread boundary.
- Create the next handoff as a living document for coding, debugging, research, review, planning, documentation, issue triage, or skill work.
- Maintain `.codex/handoffs/current.handoff.md` as a symlink to the latest generated handoff.
- Let the next thread confirm the `current.handoff.md` target before reading one handoff and continuing the session.
- Avoid relying on handoffs as transcript summaries or duplicate requirements docs.
- Report verification only when checks failed, could not be run, or have important caveats.
- Use the bundled `templates/session-handoff-template.md` instead of storing reusable templates in project handoff directories.

## isolate

Create and work inside isolated Git worktrees for delegated or multi-thread worker tasks.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/isolate -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/isolate -g -a codex -y
```

Typical uses:

- Use `/isolate <work>` in a dispatcher thread to create a durable work request with an easy-to-type pet-name work ID and print `/isolate start <work_id>` for a new worker thread.
- Allocate a fresh adjective-noun pair on collision instead of creating numbered names.
- Use `/isolate start <work_id>` in a worker thread so all implementation happens inside a unique worktree.
- Use `/isolate finish <work_id>` in the dispatcher thread to commit worker changes, merge them, remove the worktree, delete the merged branch, and mark the request completed.
- Keep the parent thread available for planning, guidance, review, and integration while worker threads continue separately.
- Use deterministic startup, status, inbox-note, and teardown scripts for worktree lifecycle.
- Refuse cleanup when worker output is dirty or unreviewed.

## pick-up-grilling-thread

Pick up a multi-thread `grill-me` or `grill-with-docs` session in a new thread from the current grilling handoff.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/pick-up-grilling-thread -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/pick-up-grilling-thread -g -a codex -y
```

Typical uses:

- Invoke explicitly with `$pick-up-grilling-thread`; Codex does not select it implicitly.
- Resume a grilling stream in a new thread from `.codex/handoffs/current.handoff.md`.
- Confirm the `current.handoff.md` target before reading one handoff.
- Identify the current decision frontier and continue with the next grilling question.
- Create the next living handoff for the current thread and update `current.handoff.md`.
- Avoid relying on handoffs as transcript summaries or duplicate requirements docs.
- Report verification only when checks failed, could not be run, or have important caveats.
- Use the bundled `templates/grill-handoff-template.md` instead of storing reusable templates in project handoff directories.

## manage-personal-skills

Audit, install, rename, remove, and sync personal Codex skills while preserving the boundary between personal source skills and third-party installed skills.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/manage-personal-skills -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/manage-personal-skills -g -a codex -y
```

Typical uses:

- Audit drift between `~/skills`, `~/.agents/skills`, and `~/.codex/skills`.
- Keep third-party skills out of the personal source repo.
- Normalize Codex runtime entries to symlinks into `.agents/skills`.

## advise-reasoning-effort

Suggest the appropriate Codex reasoning effort before substantial work starts.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/advise-reasoning-effort -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/advise-reasoning-effort -g -a codex -y
```

Typical uses:

- Recommend `low`, `medium`, `high`, or `xhigh` reasoning effort based on task complexity.
- Stay silent when the default effort is appropriate.
- Give one short proactive note before high-risk or long-running work.

## improve-feature

Improve a feature across iterations after the first implementation exists.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/improve-feature -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/improve-feature -g -a codex -y
```

Typical uses:

- Define the bar for a UI, component, API, or flow before changing it.
- Capture before/after evidence with the same settings.
- Fix only the highest-impact problem in each pass.
- Keep changes only when the measured bar improves and guardrails stay green.

## scythe

Bootstrap and operate the Scythe control plane from any Codex project directory using its durable checkpoint and live Lucia state.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/scythe -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/scythe -g -a codex -y
```

Typical uses:

- Invoke explicitly with `$scythe`; Codex does not select it implicitly.
- Use it in a fresh thread from any directory to load the current objective, frontier, worker exceptions, and exact next action without handoff confirmation.
- Keep `control-plane.md` as a sub-16-KiB current-state index with a fixed section schema; bootstrap rejects historical diaries, stale controller claims, unexpected sections, and gapped next actions.
- Make ordinary `status` a machine-readable, mutation-free observation: it never edits checkpoints or registries, dispatches or recovers workers, enqueues ingress, restarts services, triggers releases, pushes, or requests compaction.
- Enforce the bootstrap's machine-readable act-before-final gate only for `$scythe`, `continue`, or another acting request while safe immediate work or a recoverable control-plane fault remains.
- Return control immediately when Lucia owns the asynchronous next action; wait or monitor only when the user explicitly requests it.
- Read live Codex context and pace-aware weekly allowance pressure without exposing conversation content.
- Enforce a machine-readable weekly pacing gate before new model-backed work: allow a 5-point startup burst, preserve a 5-point end reserve, keep one active model worker, and never assume a manual reset.
- Run Scythe control-plane threads on Sol/xhigh by explicit operator choice while continuing to route workers at the lowest effort that meets their evidence bar.
- Route clear workers to Luna and normal implementation workers to Terra.
- Launch every delegated worker through Lucia's top-level background `codex exec` path; never use native controller-child subagents for Scythe work.
- Detect late-period surplus and recommend one measured intelligence/effort increase for the next quota window.
- Keep one permanent authoritative controller thread. At 150k input tokens, rely on native compaction in that same thread; never create a successor merely because context is large. The legacy rollover CLI is compatibility-safe and can only request current-thread compaction.
