---
name: isolate
description: Create and work inside an isolated Git worktree for delegated or multi-thread worker tasks. Use when the user invokes /isolate, asks to start an isolated worker thread, delegates work to another Codex thread, or wants deterministic startup/status/teardown around worktrees.
---

# Isolate

Use this skill in a worker thread that must do all repository work inside a dedicated Git worktree. The parent thread stays responsible for planning, dispatch, review, and integration.

## Worker Contract

When invoked in a worker thread:

1. Read the user's worker brief and repo `AGENTS.md`.
2. Start or enter the assigned worktree before editing files.
3. Run all commands and file edits from the isolated worktree path.
4. Do not edit the source checkout after isolation starts.
5. Keep to the assigned ownership scope. Ask before touching files outside it.
6. Check `.codex/isolate/inbox.md` at startup, before major edits, before tests, and before the final response.
7. Report changed paths, tests/checks run, remaining risks, branch, and worktree path.
8. Do not remove the worktree while it has uncommitted changes.

If the current thread is the dispatcher, do not implement the delegated work. Produce a worker brief that can be pasted into a new thread with `/isolate`.

## Startup

Use the bundled script to create a unique worktree and branch:

```zsh
~/skills/isolate/scripts/isolate-start.zsh --repo /path/to/repo --task "short task name" --base HEAD --owner "files or dirs this worker may edit"
```

The script refuses to reuse an existing branch or directory. It writes worker metadata and an inbox under `.codex/isolate/` inside the new worktree.

After startup, `cd` into the printed worktree path and continue from there.

## Status

Use status before handoff, after meaningful edits, and whenever the parent asks:

```zsh
~/skills/isolate/scripts/isolate-status.zsh --worktree /path/to/worktree
```

Status should be summarized to the parent thread, not pasted in full unless the output is short or the parent asks for exact output.

## Parent Guidance

Parent threads should not interrupt worker threads for ordinary guidance. Append guidance to the worker inbox:

```zsh
~/skills/isolate/scripts/isolate-note.zsh --worktree /path/to/worktree --message "Queued guidance for the worker."
```

The worker must check the inbox at the next checkpoint. If guidance invalidates current work, the parent should tell the worker directly in that worker thread.

## Teardown

Only remove clean worktrees:

```zsh
~/skills/isolate/scripts/isolate-teardown.zsh --worktree /path/to/worktree
```

The teardown script refuses primary checkouts, dirty worktrees, and non-worktree paths. It removes the worktree and prunes Git worktree metadata. It does not delete branches; branch deletion requires a separate explicit decision.

## Worker Brief Template

```text
/isolate
Repo: /absolute/path/to/repo
Base: HEAD or branch/ref
Task: one concrete outcome
Branch: worker/<slug> (optional)
Ownership: exact files/directories this worker may edit
Do not touch: files/directories to avoid
Acceptance: checks or observable behavior required
Return: worktree path, branch, changed paths, tests/checks, risks
```
