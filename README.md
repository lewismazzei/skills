# Agent Skills

The agent skills I use: my own, plus every third-party skill I have installed.

## How this repo works

- `skills.json` lists every installed skill with its source repository, pinned commit, agents, and why I keep it.
- `./install.sh` installs exactly that list. `./install.sh --dry-run` prints the commands instead.
- To update a skill, move its pin to a reviewed commit at least three days old, then run `./install.sh`.
- My own skills live in top-level directories, each with a section below.
- A third-party skill I have modified lives under a folder named for its source, with the source's licence and a `CHANGES.md`.

Skills that other tools install themselves, such as terminal-browser's, are not listed.

## pstack/architect

My copy of [pstack](https://github.com/cursor/plugins/tree/main/pstack)'s `architect` skill (Lauren Tan, MIT), without its optional step that points to `interrogate`, which I don't install. `pstack/architect/CHANGES.md` records the upstream commit and the change.

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
