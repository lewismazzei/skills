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
/home/codex/skills/manage-personal-skills/scripts/audit-skills.sh
```

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

- Audit drift between `/home/codex/skills`, `/home/codex/.agents/skills`, and `/home/codex/.codex/skills`.
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
