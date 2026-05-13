---
name: pick-up-grilling-thread
description: Pick up a multi-thread grill-me or grill-with-docs stream in a new thread from the current grilling handoff. Use when the user invokes /pick-up-grilling-thread, asks to pick up or resume a grilling thread, continue a grill-with-docs stream from a handoff, or start the next thread for a design/domain grilling session.
---

# Pick Up Grilling Thread

## Purpose

Resume one grilling stream after it crosses a thread boundary. A stream is a single `grill-me` or `grill-with-docs` session split only for context preservation.

This skill belongs at the start of the new thread. It reads the previous thread's generated handoff after confirmation, identifies the current decision frontier, asks the next question, and starts the next living handoff for the current thread.

Use normal thread continuity and auto compaction inside one active thread. Use this skill only when picking up a grilling stream in a new thread or after a deliberate reset where the current handoff pointer is the source of truth.

## Invocation Modes

### Pick Up From Current Pointer

When the user invokes this skill without naming a specific handoff:

1. Check `.codex/handoffs/current.handoff.md` only.
2. If it is missing, not a symlink, or broken, stop and tell the user. Do not scan for latest files or guess.
3. If it is a valid symlink, inspect only the symlink target path or filename.
4. Tell the user what target handoff it points to and ask for confirmation before reading the target file.
5. Read the handoff contents only after the user confirms.
6. Read `AGENTS.md` and any source-of-truth paths named in the handoff that are necessary to continue the next question.
7. Identify the current decision branch, next question, and recommended answer.
8. Create the next living handoff for this thread and update `current.handoff.md` to point to it.
9. Continue by asking one grilling question with the recommended answer.

Suggested confirmation:

```text
`.codex/handoffs/current.handoff.md` points to `[target]`. Is this the handoff you want me to read?
```

### Pick Up From Named Handoff

When the user explicitly names a handoff path, inspect that path and ask for confirmation before reading it unless the user has already explicitly asked you to read that exact file. After reading it, follow the same pickup flow: identify the frontier, create the next living handoff, update the current pointer, and ask the next question.

## Living Handoff For This Thread

After reading the confirmed source handoff:

- Use the bundled template at `templates/grill-handoff-template.md` when creating the new living handoff.
- Generate a resume point, not a transcript summary.
- Prefer the filename pattern `.codex/handoffs/[stream-slug]-ptN-ptNplus1.handoff.md`.
- Update `.codex/handoffs/current.handoff.md` to point to the new living handoff.
- Treat the new handoff as the current thread's living handoff.

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

Update the living handoff after approved doc edits, after meaningful decision branches close, before compaction, and whenever the user asks to preserve the current state for another thread.

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
- Never read handoff contents before the user confirms the `current.handoff.md` target, unless the user explicitly names and asks you to read an exact handoff path.

## Bundled Template

Use `templates/grill-handoff-template.md` as the starting structure for new grill-session handoffs. Do not store reusable templates in `.codex/handoffs/`; that directory should contain generated handoffs only.

## Output

After picking up the thread, tell the user:

- The source handoff path read.
- The new living handoff path.
- The `current.handoff.md` symlink target.
- Any source-of-truth docs changed.
- The next grilling question and recommended answer.
- Verification only when checks failed, could not be run, or have important caveats; omit a "verification passed" line when checks succeed.
