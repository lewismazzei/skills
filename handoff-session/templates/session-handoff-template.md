# Handoff: [Session Name], Part [N] To Part [N+1]

Target model/runtime:
[Target model] in [runtime]. If a later part runs on a newer model, preserve this handoff's product contract and follow current prompt guidance for that model.

Working directory:
`[absolute repo path]`

Current session:
This is a living handoff for one coherent work session spread across multiple threads solely for context preservation. Keep it current during part [N] so part [N+1] can continue without rediscovering context.

## Hybrid Context Policy

- Use normal thread continuity and auto compaction inside a single active thread.
- Use explicit handoffs when crossing thread boundaries, when the user invokes the handoff skill, before a deliberate reset, or when context loss would materially harm the session.
- The handoff is a resume point, not a transcript summary.
- If maintaining the handoff starts interrupting flow, defer updates until a meaningful state change lands, a source-of-truth edit lands, verification completes, or the thread is about to end.

## Handoff Invariant

A future agent should be able to read `AGENTS.md` plus this handoff, identify the current state frontier, honor active constraints, perform the next action, avoid known bad paths, and continue the same session without reading the transcript.

Do not hand off the transcript. Hand off the current state frontier.

## Current Pointer Policy

`.codex/handoffs/current.handoff.md` should be a symlink to the latest generated handoff for this session.

- When this handoff is created or updated, update `current.handoff.md` to point to it.
- In a new thread, `/handoff-session` should default to checking `current.handoff.md`.
- Before reading handoff contents, inspect only the symlink target and ask the user to confirm it is the intended handoff.
- If `current.handoff.md` is missing, not a symlink, or broken, stop and tell the user. Do not guess the latest handoff by filename.
- `.codex/handoffs/` should contain generated handoffs and the current pointer only; reusable templates live inside the skill.

## Prompt Posture

- Keep the handoff outcome-first: state the frontier, objective, constraints, evidence, side-effect boundaries, and stopping rules before process details.
- Use concise, direct wording. Do not expand the handoff into a second requirements document, PRD, ADR, postmortem, changelog, test report, or transcript.
- Prefer "what changed since the previous handoff" over narrative history.
- Keep process guidance only where the path matters for preserving source-of-truth discipline, side-effect safety, approval gates, or verification.
- Preserve completed actions, assumptions, IDs, tool results, blockers, and the next concrete action when compacting or handing off.

## Frontier

Objective:
[One-sentence outcome for this session.]

Current status:
[Where the work stands now.]

Current phase or branch:
[The active phase, decision branch, debugging hypothesis, implementation area, research thread, or review focus.]

Exact next action:
[The next concrete action for the following thread.]

If user input is needed, ask:
[Single question.]

Recommended answer or recommendation:
[The recommendation to present with the question, or "not needed".]

Why it matters:
[The boundary, dependency, risk, decision, workflow, or source-of-truth issue this resolves.]

Known dependencies:
[Earlier decisions, facts, files, or external state that constrain the next action.]

Stopping rule:
[When to stop, ask, update docs, verify, commit, deploy, or hand off.]

## Carry-Forward Handoff Rule

This rule is intentionally durable. Every future thread in this session must carry it forward into the next handoff.

- After reading the latest handoff, immediately create the next handoff file while context is fresh.
- Treat that next handoff as a living document for the lifetime of the thread.
- Add resolved decisions, open questions, source-of-truth edits, verification results, caveats, files changed, external IDs, and next actions as work happens.
- Before ending the thread, update the living handoff so the next part can start from accurate state.
- Update `.codex/handoffs/current.handoff.md` to point to the living handoff.
- Copy this carry-forward rule into each new handoff so part N automatically prepares part N+1.
- Do not duplicate content already captured in other artifacts, including PRDs, plans, ADRs, issues, commits, diffs, `CONTEXT.md`, product docs, issue trackers, code, logs, or prior handoffs. Reference them by path, ID, commit, diff, or URL instead.

Update the living handoff:

- After a meaningful state change lands.
- After any approved source-of-truth edit.
- After a path is rejected, deferred, or split.
- After important verification results.
- Before compaction or context handoff.
- Before ending the thread.

Suggested next filename pattern:
`.codex/handoffs/[session-slug]-ptN-ptNplus1.handoff.md`

## User And Repo Instructions To Preserve

- [Repo-specific instruction.]
- [User-specific instruction.]
- [Side-effect boundary, such as "Do not edit Linear unless explicitly asked."]
- [Doc-update boundary, such as "Update CONTEXT.md after approved domain terminology decisions."]

## Success Criteria

- The active state frontier is explicit.
- The next action is concrete.
- Open questions and blockers are visible.
- Settled decisions are captured in the correct durable source of truth.
- Deferred decisions and rejected paths are recorded without becoming requirements.
- Verification expectations are clear.
- Allowed side effects are respected.

## Source Of Truth

Read these before continuing:

- `[file path]`
- `[file path]`
- Prior handoffs:
  - `[file path]`

Source-of-truth boundary:

- If a decision is already captured in durable docs, issue trackers, ADRs, commits, diffs, code, generated artifacts, logs, or another artifact, this handoff should point to it rather than restating it.
- This handoff should capture only the current frontier: active phase, next action, decisions made during this part, open questions, failed or rejected paths, files/state, verification, and caveats.
- Do not let the handoff become the authoritative home for requirements, rationale, domain language, implementation details, or verification output that belongs in durable artifacts.

## External System Context

[Issue tracker, project, milestone, branch, PR, deployment, environment, database, automation, or other IDs.]

Allowed side effects:

- [Read-only/read-write boundary.]
- [Required explicit approvals.]

## Completed Since Previous Handoff

- [Action completed, with path/ID if relevant.]

## Decisions Made In This Part

- [Decision, with durable source path if any.]

## Open Questions Or Blockers

- [Question or blocker.]

## Failed, Rejected, Or Deferred Paths

- [Path and reason.]

## Standing Constraints

- [Constraint.]
- [Terminology, architecture, workflow, or source-of-truth rule.]

Stale terms or bad paths to avoid unless quoted as source material:

- `[term]`

## Files And State

Files changed:

- `[path]` - [change summary]

Commands, tools, or checks run:

- `[command/tool]` - [result summary]

Worktree caveat:
[Current `git status --short` caveat or branch state.]

Do not revert or clean unrelated changes unless the user explicitly asks.

## Verification Expectations

After relevant edits, run:

```sh
[verification command]
```

Expected caveats:

- [Known false positive or allowed exception.]

## Compaction Instructions

If the thread compacts or is handed off, preserve:

- Objective.
- Current status.
- Current phase or branch.
- Exact next action.
- Decisions made since the last handoff update.
- Open questions and blockers.
- Failed, rejected, or deferred paths.
- Files changed.
- External IDs or systems touched.
- Verification run.
- Worktree caveats.

## Suggested Skills Or Tools

- `handoff-session` before ending or crossing a multi-thread session.
- `[other skill/tool]` for [when to use it].

## Work Log

### [YYYY-MM-DD]

- [Action completed.]

## Next Concrete Action

[Single next action.]

If user input is needed, ask:

[Single question, with the recommendation.]
