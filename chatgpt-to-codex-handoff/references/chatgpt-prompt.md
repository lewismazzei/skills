# ChatGPT Prompt For Codex Handoffs

Use this prompt inside ChatGPT or a ChatGPT Project when you are ready to move a discussion into Codex for local repo work.

```text
Prepare a concise handoff for Codex from this ChatGPT conversation or Project.

The goal is not to summarize the whole conversation chronologically. The goal is to give Codex the minimum actionable context needed to inspect the right local files, make the next change, and verify it without broad rediscovery.

Output your handoff in a fenced `markdown` code block using exactly this structure:

```markdown
# Codex Handoff
...
```

Inside that fenced block, use this structure:

# Codex Handoff

## Goal
State the outcome we are trying to achieve.

## Current State
Summarize what already exists, what has been discussed, and what matters for the next Codex action.

## Relevant Files / Repos
Separate known facts from assumptions.

- Known: files, folders, branches, commands, docs, URLs, or repo areas explicitly discussed.
- Likely: inferred files or areas Codex should inspect first. Mark these as assumptions.

## Constraints
List product, design, technical, security, budget, usage, style, or process constraints that Codex should respect.

## Decisions Made
List important decisions and short reasons. Include only decisions that affect implementation or verification.

## Tried / Rejected
List approaches, fixes, or ideas already considered, tried, or rejected, with the reason if known.

## Open Questions
List unresolved questions. Mark which ones are blocking Codex from acting now. If none are blocking, say so.

## Next Task
Give Codex one concrete next task to perform first. Make it specific enough that Codex can start with targeted local inspection.

## Verification
Describe how Codex should check success: commands to run, tests to update, UI flow to verify, expected behavior, or acceptance criteria.

Optional sections, only if useful:

## Links / References
Include docs, issues, PRs, designs, specs, or messages Codex may need.

## Commands
Include exact commands already discussed or likely needed.

## Risks
Call out fragile areas, migration concerns, privacy/security issues, or likely regressions.

## Out of Scope
List things Codex should not do in this pass.

Rules:
- Optimize for actionability first, compactness second.
- Default length should be about 500-1,200 words.
- For tiny tasks, use 150-400 words.
- For complex multi-file work, use up to 2,000 words.
- Do not exceed 2,000 words unless I explicitly ask for an archival handoff.
- Do not include nice-to-know background.
- Do not include long verbatim transcript excerpts.
- Use verbatim snippets only for exact specs, user wording, API payloads, error messages, prompts, or acceptance criteria that must be preserved.
- Label uncertainty as an assumption instead of inventing details.
- Redact secrets, credentials, private tokens, and unnecessary personal data.
- Before finalizing, remove any detail that does not help Codex decide what to inspect, edit, test, or ask next.
```
