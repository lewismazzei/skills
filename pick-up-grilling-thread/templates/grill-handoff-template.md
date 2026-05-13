# Handoff: [Stream Name], Part [N] To Part [N+1]

Target model/runtime:
[Target model] in [runtime]. If a later part runs on a newer model, preserve this handoff's product contract and follow current prompt guidance for that model.

Working directory:
`[absolute repo path]`

Current stream:
This is a living handoff for one `grill-me` or `grill-with-docs` session spread across multiple threads solely for context preservation. Keep it current during part [N] so part [N+1] can continue the same grilling stream without rediscovering context.

## Hybrid Context Policy

- Use normal thread continuity and auto compaction inside a single active thread.
- Use explicit handoffs when crossing thread boundaries, when the user invokes the handoff skill, before a deliberate reset, or when context loss would materially harm the decision stream.
- The handoff is a resume point, not a transcript summary.
- If maintaining the handoff starts interrupting the grilling flow, defer updates until a branch closes, a source-of-truth edit lands, or the thread is about to end.

## Handoff Invariant

A future agent should be able to read `AGENTS.md` plus this handoff, identify the current decision frontier, ask the next question, avoid known bad paths, and continue the same grilling stream without reading the transcript.

Do not hand off the transcript. Hand off the current state frontier.

## Current Pointer Policy

`.codex/handoffs/current.handoff.md` should be a symlink to the latest generated handoff for this grilling stream.

- When this handoff is created or updated, update `current.handoff.md` to point to it.
- In a new thread, `/pick-up-grilling-thread` should default to checking `current.handoff.md`.
- Before reading handoff contents, inspect only the symlink target and ask the user to confirm it is the intended handoff.
- If `current.handoff.md` is missing, not a symlink, or broken, stop and tell the user. Do not guess the latest handoff by filename.
- `.codex/handoffs/` should contain generated handoffs and the current pointer only; reusable templates live inside the skill.

## Prompt Posture

- Keep the handoff outcome-first: state the frontier, success criteria, constraints, evidence requirements, and stopping rules before process details.
- Use concise, direct wording. Do not expand the handoff into a second requirements document, PRD, ADR, or transcript.
- Prefer "what changed since the previous handoff" over narrative history.
- Keep process guidance only where the path matters for preserving source-of-truth discipline, side-effect safety, approval gates, or verification.
- State reasoning and verbosity expectations separately from final answer length.
- Use short preambles before tool-heavy work when the user benefits from visible progress.
- Preserve completed actions, assumptions, IDs, tool results, blockers, and the next concrete goal when compacting or handing off.

## Frontier

Current grilling mode:
[`grill-me` or `grill-with-docs`.]

Current decision branch:
[The branch of the decision tree currently being resolved.]

Current question:
[The exact next question to ask the user.]

Recommended answer:
[The recommended answer to present with the question.]

Why it matters:
[The boundary, dependency, terminology, workflow, or source-of-truth decision this resolves.]

Known dependencies:
[Earlier decisions or facts that constrain this question.]

Stopping rule:
[When to stop, ask, update docs, verify, or hand off.]

## Carry-Forward Handoff Rule

This rule is intentionally durable. Every future thread in this grilling stream must carry it forward into the next handoff.

- After reading the latest handoff, immediately create the next handoff file while context is fresh.
- Treat that next handoff as a living document for the lifetime of the thread.
- Add resolved decisions, open branches, source-of-truth edits, verification results, caveats, and next actions as work happens.
- Before ending the thread, update the living handoff so the next part can start from accurate state.
- Update `.codex/handoffs/current.handoff.md` to point to the living handoff.
- Copy this carry-forward rule into each new handoff so part N automatically prepares part N+1.
- Do not duplicate content already captured in other artifacts, including PRDs, plans, ADRs, issues, commits, diffs, `CONTEXT.md`, product docs, issue trackers, code, or prior handoffs. Reference them by path, ID, commit, diff, or URL instead.

Update the living handoff:

- After a meaningful decision branch closes.
- After any approved source-of-truth edit.
- After a branch is rejected, deferred, or split.
- Before compaction or context handoff.
- Before ending the thread.

Suggested next filename pattern:
`.codex/handoffs/[stream-slug]-ptN-ptNplus1.handoff.md`

## User And Repo Instructions To Preserve

- [Repo-specific instruction.]
- [User-specific instruction.]
- [Side-effect boundary, such as "Do not edit Linear unless explicitly asked."]
- [Doc-update boundary, such as "Update CONTEXT.md immediately after approved domain terminology decisions."]

## Goal

[One-sentence outcome for this grilling stream.]

Success criteria for the stream:

- The active decision tree is explicit.
- Each question is asked one at a time.
- Each question includes the agent's recommended answer.
- Resolved decisions are captured in the correct durable source of truth.
- Deferred decisions and rejected paths are recorded without becoming requirements.
- Verification runs after approved source-of-truth edits.
- Allowed side effects are respected.

## Source Of Truth

Read these before continuing:

- `[file path]`
- `[file path]`
- Prior handoffs:
  - `[file path]`

Source-of-truth boundary:

- If a decision is already captured in durable docs, issue trackers, ADRs, commits, diffs, code, or another artifact, this handoff should point to it rather than restating it.
- This handoff should capture only the current frontier: active branch, current question, decisions made during this part, open questions, failed or rejected paths, files/state, verification, and next action.
- Do not let the handoff become the authoritative home for requirements, rationale, or domain language that belongs in durable docs.
- For `grill-with-docs`, durable domain language belongs in the repo's domain docs, while delivery scope belongs in product specs or issue trackers.
- For `grill-me`, use the handoff to preserve decisions unless the user has named a durable source of truth.

## External System Context

[Issue tracker, project, milestone, branch, PR, deployment, or other IDs.]

Allowed side effects:

- [Read-only/read-write boundary.]
- [Required explicit approvals.]

## Resolved Branches

Treat these as settled unless the user explicitly asks to revisit them or a real contradiction appears:

- [Branch] - [resolved decision, with durable source path if any].

## Open Branches

Continue with these branches. Notes are starting hypotheses only:

- [Branch].
  - Current uncertainty: [uncertainty].
  - Likely next question: [question].
  - Likely durable source: [path or "handoff only"].

## Decisions Made In This Part

- [Decision.]

## Failed Or Rejected Paths

- [Rejected path and reason.]

## Standing Constraints

- [Constraint.]
- [Terminology or source-of-truth rule.]

Stale terms or bad paths to avoid unless quoted as source material:

- `[term]`

## Verification Expectations

After source-of-truth edits, run:

```sh
[verification command]
```

Expected caveats:

- [Known false positive or allowed exception.]

## Compaction Instructions

If the thread compacts or is handed off, preserve:

- Objective.
- Current grilling mode.
- Current decision branch.
- Current question and recommended answer.
- Decisions made since the last handoff update.
- Open questions.
- Failed or rejected paths.
- Files changed.
- Verification run.
- Exact next action.

## Worktree Caveat

[Current `git status --short` caveat or branch state.]

Do not revert or clean unrelated changes unless the user explicitly asks.

## Suggested Skills Or Tools

- `grill-me` for plan/design stress-testing without doc updates.
- `grill-with-docs` for domain/design stress-testing that should update durable docs as decisions crystallize.
- `pick-up-grilling-thread` when starting a new thread from the current grilling handoff.
- `[other skill/tool]` for [when to use it].

## Work Log

### [YYYY-MM-DD]

- [Action completed.]

## Next Concrete Action

[Single next action.]

If user input is needed, ask:

[Single question, with the recommended answer.]
