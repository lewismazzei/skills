---
name: handoff-grilling-session
description: Create or update a living handoff for a multi-thread grill-me or grill-with-docs session. Use when the user invokes /handoff-grilling-session, asks to hand off a grilling session, continue a grill-with-docs stream, preserve context across threads, or prepare the next thread for a design/domain grilling session.
---

# Handoff Grill Thread

## Purpose

Maintain a living handoff for one grilling stream spread across multiple threads. A stream is a single `grill-me` or `grill-with-docs` session split only for context preservation.

The handoff should let the next thread read `AGENTS.md` plus the generated handoff and continue by asking the next question.

Use normal thread continuity and auto compaction inside one active thread. Use this skill when crossing a thread boundary, when the user invokes it, before a deliberate reset, or when context loss would materially harm the decision stream.

## Invocation Modes

### Resume In A New Thread

When the user invokes this skill in a new thread without naming a specific handoff:

1. Check `.codex/handoffs/current.handoff.md` only.
2. If it is missing, not a symlink, or broken, stop and tell the user. Do not scan for latest files or guess.
3. If it is a valid symlink, inspect only the symlink target path or filename.
4. Tell the user what target handoff it points to and ask for confirmation before reading the target file.
5. Read the handoff contents only after the user confirms.

Suggested confirmation:

```text
`.codex/handoffs/current.handoff.md` points to `[target]`. Is this the handoff you want me to read?
```

### Create Or Update A Handoff

1. Find the latest relevant handoff under `.codex/handoffs/`.
2. If no next handoff exists, create one immediately while context is fresh.
3. Use the bundled template at `templates/grill-handoff-template.md` when creating a new handoff.
4. Generate a resume point, not a transcript summary.
5. Update `.codex/handoffs/current.handoff.md` to point to the generated handoff.

## Handoff Content

Keep the handoff as state frontier:
   - current grilling mode
   - current decision branch
   - next question and recommended answer
   - resolved branches
   - open branches
   - source-of-truth edits
   - rejected or deferred paths
   - verification run
   - exact next action

For `grill-with-docs`, point to durable docs instead of duplicating settled decisions.

For `grill-me`, preserve decisions in the handoff unless the user named another durable source of truth.

Update the handoff before compaction, before ending the thread, after approved doc edits, and after meaningful decision branches close.

## Current Pointer

`.codex/handoffs/current.handoff.md` is a symlink only, never a real handoff file.

When creating or updating a handoff:

- Update `current.handoff.md` to point to that handoff.
- Prefer a relative symlink target from `.codex/handoffs/`.
- If `current.handoff.md` exists and is not a symlink, stop and ask the user before touching it.
- Do not store reusable templates in `.codex/handoffs/`; that directory should contain generated handoffs and the current pointer only.

## Rules

- Ask one question at a time when continuing the grilling session.
- Include the agent's recommended answer with each question.
- Do not turn the handoff into a PRD, ADR, requirements doc, or transcript.
- Do not duplicate content already captured in other artifacts, including PRDs, plans, ADRs, issues, commits, diffs, `CONTEXT.md`, product docs, issue trackers, or code. Reference them by path, ID, commit, diff, or URL instead.
- Do not make handoff upkeep interrupt every conversational turn; keep it lightweight and frontier-focused.
- Keep allowed side effects explicit, especially whether docs or external systems may be edited.
- If creating the next handoff, carry forward the handoff rule so the following thread repeats this process.
- In resume mode, never read handoff contents before the user confirms the `current.handoff.md` target.

## Bundled Template

Use `templates/grill-handoff-template.md` as the starting structure for new grill-session handoffs. Do not store reusable templates in `.codex/handoffs/`; that directory should contain generated handoffs only.

## Output

After updating the handoff, tell the user:

- The handoff path.
- The `current.handoff.md` symlink target, if updated.
- Whether a next handoff was created or an existing handoff was updated.
- Any source-of-truth docs changed.
- Verification only when checks failed, could not be run, or have important caveats; omit a "verification passed" line when checks succeed.
