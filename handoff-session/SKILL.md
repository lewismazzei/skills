---
name: handoff-session
description: Create or update a living handoff for a multi-thread work session. Use when the user invokes /handoff-session, asks to hand off or resume a session, preserve context across threads, prepare the next thread, or continue work from a current handoff outside a grilling-only stream.
---

# Handoff Session

## Purpose

Maintain a living handoff for one coherent work session spread across multiple threads. A session may be coding, debugging, research, review, planning, documentation, issue triage, skill work, or another focused stream split for context preservation.

The handoff should let the next thread read `AGENTS.md` plus the generated handoff and continue from the current state frontier without rediscovering context.

Use normal thread continuity and auto compaction inside one active thread. Use this skill when crossing a thread boundary, when the user invokes it, before a deliberate reset, or when context loss would materially harm the work stream.

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

### Resume From A Named Handoff

When the user names a specific handoff file, read that file and continue from it. If the named path conflicts with `.codex/handoffs/current.handoff.md`, mention the mismatch before changing the pointer.

### Create Or Update A Handoff

1. Find the latest relevant handoff under `.codex/handoffs/` when the active session already has one.
2. If no relevant handoff exists, create one immediately while context is fresh.
3. Use the bundled template at `templates/session-handoff-template.md` when creating a new handoff.
4. Generate a resume point, not a transcript summary.
5. Update `.codex/handoffs/current.handoff.md` to point to the generated handoff.

## Handoff Content

Keep the handoff as state frontier:

- objective and current status
- current phase or branch of work
- exact next action
- blockers and open questions
- recommended answer or recommendation when user input is needed
- decisions made since the last handoff
- durable source-of-truth references
- files, commands, tools, issues, PRs, deployments, or external IDs involved
- verification run and remaining caveats
- rejected or deferred paths
- allowed side effects and approval boundaries
- worktree or environment caveats

Point to durable docs, issue trackers, commits, diffs, code, plans, PRDs, ADRs, tickets, or prior handoffs instead of duplicating their settled content.

Update the handoff before compaction, before ending the thread, after approved source-of-truth edits, after meaningful state changes, and after important verification results.

## Current Pointer

`.codex/handoffs/current.handoff.md` is a symlink only, never a real handoff file.

When creating or updating a handoff:

- Update `current.handoff.md` to point to that handoff.
- Prefer a relative symlink target from `.codex/handoffs/`.
- If `current.handoff.md` exists and is not a symlink, stop and ask the user before touching it.
- Do not store reusable templates in `.codex/handoffs/`; that directory should contain generated handoffs and the current pointer only.

## Rules

- Do not turn the handoff into a PRD, ADR, requirements doc, postmortem, changelog, test report, or transcript.
- Do not duplicate content already captured in other artifacts, including PRDs, plans, ADRs, issues, commits, diffs, `CONTEXT.md`, product docs, issue trackers, code, or prior handoffs. Reference them by path, ID, commit, diff, or URL instead.
- Keep handoff upkeep lightweight and frontier-focused.
- Keep allowed side effects explicit, especially whether code, docs, git state, deployments, or external systems may be edited.
- Preserve user instructions, repo instructions, constraints, and approval gates that the next thread must honor.
- Preserve commands and verification as summarized facts unless exact output is essential.
- Keep secrets, credentials, tokens, and private keys out of handoffs.
- If creating the next handoff, carry forward the handoff rule so the following thread repeats this process.
- In resume mode, never read handoff contents before the user confirms the `current.handoff.md` target.

## Output

After updating the handoff, tell the user:

- The handoff path.
- The `current.handoff.md` symlink target, if updated.
- Whether a next handoff was created or an existing handoff was updated.
- Any source-of-truth docs or external systems changed.
- Verification only when checks failed, could not be run, or have important caveats; omit a "verification passed" line when checks succeed.
