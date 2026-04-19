# Agent Skills

Personal agent skills for AI coding agents.

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
