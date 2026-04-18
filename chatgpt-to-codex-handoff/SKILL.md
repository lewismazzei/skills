---
name: chatgpt-to-codex-handoff
description: Prepare, review, and consume structured handoffs from ChatGPT chats or ChatGPT Projects into Codex. Use when the user wants to bring ChatGPT context into Codex, asks for a Codex handoff prompt, invokes "/chatgpt-to-codex-handoff prompt", says "use this Codex handoff", pastes a "# Codex Handoff", wants to continue from ChatGPT, wants to review a handoff before acting, or wants a concise return handoff from Codex back to ChatGPT while minimizing rediscovery.
---

# ChatGPT to Codex Handoff

Use this skill to move context from ChatGPT into Codex without restarting broad discovery. Treat the handoff as an execution contract: trust it enough to focus the work, verify local facts before editing, and ask only when blocked.

## Mode Selection

Infer the mode from the user request:

- **Slash prompt command**: If the user invokes `/chatgpt-to-codex-handoff prompt`, `/chatgpt-to-codex-handoff chatgpt-prompt`, or a bare `/chatgpt-to-codex-handoff` with no pasted handoff or task, read `references/chatgpt-prompt.md` and return it as a copyable fenced `text` block. Do not inspect local files or start implementation.
- **Produce handoff prompt**: The user asks for a prompt to summarize a ChatGPT chat or Project for Codex. Read `references/chatgpt-prompt.md` and return a lightly adapted copyable prompt.
- **Review handoff**: The user asks whether a handoff is good enough, complete, or actionable. Evaluate it and suggest fixes; do not implement.
- **Consume handoff**: The user pastes a `# Codex Handoff` or says to continue from a handoff. Parse it, validate it, inspect targeted local context, then execute the next task if unblocked.
- **Return handoff**: The user asks to hand Codex work back to ChatGPT or summarize the Codex session for ChatGPT. Produce a concise `# ChatGPT Return Handoff`.

If the mode is ambiguous and different modes would produce materially different output, ask one concise question.

## Handoff Format

Prefer human-readable Markdown with these sections:

```md
# Codex Handoff

## Goal
## Current State
## Relevant Files / Repos
## Constraints
## Decisions Made
## Tried / Rejected
## Open Questions
## Next Task
## Verification
```

Optional sections:

```md
## Links / References
## Commands
## Risks
## Out of Scope
```

Treat `Goal`, `Next Task`, and `Verification` as required before making code changes. Missing optional sections are acceptable. If a required section is missing, ask the single question that unlocks the next local action, or provide the ChatGPT-side prompt if no usable handoff exists.

For file context, distinguish facts from hints:

- **Known**: files, folders, branches, commands, docs, or links explicitly discussed.
- **Likely**: inferred areas Codex should inspect first. Treat these as assumptions, not facts.

## Consume Workflow

When consuming a handoff:

1. Extract the goal, next task, verification target, constraints, decisions, and file hints.
2. Reply with a 3-6 line intake summary: understood goal, next local action, verification target, and any blocking question.
3. If blocked, ask exactly one concise question. If not blocked, proceed.
4. Inspect only the named or high-likelihood local areas needed to verify claims and execute the next task.
5. Prefer local repo evidence over handoff claims when they conflict; call out the mismatch briefly.
6. Make the requested change or analysis, then verify using the handoff's `Verification` section or the closest repo-native checks.

## Usage-Efficient Behavior

Keep Codex work focused:

- Prefer the provided handoff over broad rediscovery.
- Do not summarize the whole prior ChatGPT conversation again.
- Do not ask broad product or planning questions that should have been settled in ChatGPT.
- Ask only when a missing decision would materially change the next implementation step.
- If several gaps exist, ask the one question that unlocks immediate local progress.

## Persistence

Do not save handoff content by default.

Decide whether persistence is useful. It usually is only useful for multi-session work, multi-agent coordination, risky paused work, or a handoff that will be reused. If persistence is useful, ask before writing anything.

If the user approves saving:

- Save to `.codex/handoffs/<descriptive-handoff-title>.md`.
- Use a short lower-case hyphenated title, such as `.codex/handoffs/checkout-webhook-retry-plan.md`.
- If inside a Git repo, check whether `.codex/` is ignored, for example with `git check-ignore -q .codex/` from the repo root.
- If `.codex/` is not ignored, remind the user. Do not edit `.gitignore` unless the user explicitly asks.
- Never commit handoff docs by default.
- Avoid storing secrets or unnecessary transcript content. Redact sensitive values.

## Produce Handoff Prompt

When the user asks for a ChatGPT-side prompt, read `references/chatgpt-prompt.md` and return the prompt. This is also the default behavior for `/chatgpt-to-codex-handoff prompt` and for a bare `/chatgpt-to-codex-handoff` when no pasted handoff or task is present. Adapt the wording only for the user's stated project, thread, repo, or task. Do not inspect local files unless the user explicitly asks.

## Review Handoff

When reviewing a handoff, report:

- Whether `Goal`, `Next Task`, and `Verification` are present and actionable.
- Any blocking gaps or contradictions.
- Non-blocking improvements that would reduce Codex rediscovery.
- A compact revised handoff if that is faster than describing changes.

Do not execute implementation work in review mode.

## Return Handoff

When asked to hand Codex work back to ChatGPT, output:

```md
# ChatGPT Return Handoff

## What Changed
## Files Touched
## Decisions Made In Codex
## Verification Run
## Remaining Questions
## Suggested Next ChatGPT Discussion
```

Keep it concise. Do not save it unless asked.
