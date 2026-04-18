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

- Ask for a ChatGPT-side prompt that produces a `# Codex Handoff`.
- Review a handoff before spending Codex time on implementation.
- Consume a pasted handoff and continue with targeted local repo work.
- Produce a short return handoff from Codex back to ChatGPT.
