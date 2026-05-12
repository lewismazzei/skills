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

- Preserve the current state frontier before ending or crossing a thread boundary.
- Create the next handoff as a living document for coding, debugging, research, review, planning, documentation, issue triage, or skill work.
- Maintain `.codex/handoffs/current.handoff.md` as a symlink to the latest generated handoff.
- Let the next thread confirm the `current.handoff.md` target before reading one handoff and continuing the session.
- Avoid relying on handoffs as transcript summaries or duplicate requirements docs.
- Report verification only when checks failed, could not be run, or have important caveats.
- Use the bundled `templates/session-handoff-template.md` instead of storing reusable templates in project handoff directories.

## handoff-grilling-session

Create or update a living handoff for a multi-thread `grill-me` or `grill-with-docs` session.

Install globally for Codex:

```bash
add-skill lewismazzei/skills/handoff-grilling-session -y
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/handoff-grilling-session -g -a codex -y
```

Typical uses:

- Preserve the current decision frontier before ending a grilling thread.
- Create the next handoff as a living document when crossing thread boundaries.
- Maintain `.codex/handoffs/current.handoff.md` as a symlink to the latest generated handoff.
- Let the next thread confirm the `current.handoff.md` target before reading one handoff and continuing with the next grilling question.
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
