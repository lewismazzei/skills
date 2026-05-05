---
name: guide-handoff-prompt
description: Use when creating, revising, or reviewing a handoff script, handoff prompt, subagent prompt, agent-to-agent handoff note, runbook prompt, or system/developer prompt for another AI agent or OpenAI model. Ensures the artifact identifies the target model and follows current, relevant OpenAI prompt guidance from the openai-docs skill before delivery.
---

# Handoff Prompt Guidance

Create handoff scripts that are tuned to the model that will run them. Treat OpenAI docs as the source of truth for model-specific prompt guidance; do not rely on remembered prompt tips when current docs can be fetched.

## Required Workflow

1. Identify the receiving agent context:
   - Target model or model family.
   - API surface or runtime, when relevant.
   - Task goal, expected outcome, allowed side effects, tools, inputs, and output contract.
   - Whether the handoff script is operational prompt text, a runbook, a subagent prompt, or a review checklist.

2. Resolve the model:
   - Preserve an explicitly named target model.
   - Prefer the receiving agent's model. If the handoff script is for the same agent that is creating it, use the active runtime model when it is exposed in the conversation, system context, config, or user request.
   - If the user says latest, default, or best without an observable active model, use the `openai-docs` skill workflow to fetch `https://developers.openai.com/api/docs/guides/latest-model.md` and follow its current `promptingGuide` link.
   - If only a model family is known, use the closest official guidance for that family and state the inference outside the script.
   - If the model cannot be inferred and model-specific tuning matters to the artifact, ask one concise clarifying question before finalizing.

3. Fetch relevant OpenAI prompt guidance:
   - Use `openai-docs` and the OpenAI developer docs MCP tools first.
   - Fetch the current prompt guidance for the resolved model. Prefer explicit links returned by `latest-model.md`; otherwise search official docs for the model plus "prompt guidance".
   - Fetch adjacent docs only when the handoff script needs them: reasoning controls, verbosity, structured outputs, tool calling, hosted tools, prompt caching, compaction, Agents SDK handoffs, or Responses API state handling.
   - If current docs cannot be fetched, disclose that and either use bundled `openai-docs` fallback references or stop before claiming model-specific compliance.

4. Draft or revise the handoff script:
   - Write outcome-first instructions: goal, success criteria, evidence requirements, stopping rules, and allowed side effects.
   - Keep process guidance only where the exact path matters. Prefer clear constraints over step-by-step micromanagement.
   - Put tool-specific details near tool descriptions or the tool section: when to use the tool, required inputs, side effects, retry safety, and common error modes.
   - Specify output shape through the runtime's structured output mechanism when available. If producing plain prompt text, keep formatting instructions concise and testable.
   - Set verbosity and reasoning expectations separately from final answer length.
   - Include current date or timezone context only when the task needs a non-UTC, user-local, policy-effective, or business-specific date.
   - For long-running agents, include compaction or continuation requirements that preserve completed actions, assumptions, IDs, tool results, blockers, and the next concrete goal.
   - For coding agents, include reuse expectations, delegation boundaries, verification commands, acceptance criteria, and clear continue-versus-ask-for-help rules.

5. Self-check before delivery:
   - The target model is named or the ambiguity is explicit.
   - Current OpenAI docs or a disclosed fallback informed the prompt guidance.
   - The script does not include stale assumptions, hidden API claims, or generic advice that conflicts with fetched guidance.
   - The script has concrete success criteria, stopping rules, and output expectations.
   - The script is not over-specified with unnecessary step-by-step process guidance.

## Delivery

Return the handoff script as the primary artifact. Add a short note outside the script naming the model guidance used and any unresolved ambiguity. Do not include documentation citations inside the operational script unless the user asks for an audit trail or the artifact itself needs citations.
