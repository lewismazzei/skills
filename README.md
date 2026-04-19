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

## chatgpt-to-codex-handoff

Prepare, review, and consume structured handoffs from ChatGPT chats or ChatGPT Projects into Codex. The skill is designed to move context into Codex without restarting broad discovery.

Install globally for Codex:

```bash
npx skills add https://github.com/lewismazzei/skills --skill chatgpt-to-codex-handoff -g -a codex
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/chatgpt-to-codex-handoff -g -a codex
```

Typical uses:

- Invoke `/chatgpt-to-codex-handoff prompt` to print the ChatGPT-side handoff prompt.
- Ask for a ChatGPT-side prompt that produces a `# Codex Handoff`.
- Review a handoff before spending Codex time on implementation.
- Consume a pasted handoff and continue with targeted local repo work.
- Produce a short return handoff from Codex back to ChatGPT.

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

## to-linear-issues

Convert markdown task lists or planning notes into deduplicated Linear issues.

Install globally for Codex:

```bash
npx skills add https://github.com/lewismazzei/skills --skill to-linear-issues -g -a codex
```

Direct folder install:

```bash
npx skills add https://github.com/lewismazzei/skills/tree/main/to-linear-issues -g -a codex
```

Typical uses:

- Turn unchecked markdown checklist items into Linear issues.
- Preview parsed issue titles, labels, priorities, assignees, and provenance before creation.
- Deduplicate issues with stable external keys in Linear issue descriptions.
- Sync planning docs into a target Linear team and optional project.
