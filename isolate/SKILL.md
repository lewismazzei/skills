---
name: isolate
description: Create, run, and finish isolated Git worktree requests for delegated or multi-thread worker tasks. Use when the user invokes /isolate <work>, /isolate start <work_id>, or /isolate finish <work_id>; delegates work to another Codex thread; or wants deterministic worktree startup/status/finish/teardown.
---

# Isolate

Use this skill to dispatch isolated worker requests and to run worker threads inside dedicated Git worktrees. The parent thread stays responsible for planning, dispatch, review, and integration.

## Argument Modes

### Dispatcher: `/isolate <work>`

When the user invokes `/isolate` with a work description in the main thread, create a durable work request and print the one-line prompt for a new worker thread:

```zsh
~/skills/isolate/scripts/isolate-dispatch.zsh --repo /path/to/repo --task "work description" --base HEAD --owner "files or dirs this worker may edit"
```

If the repo is not explicit, infer the nearest Git repo from the current directory. If ownership is unclear, keep it narrow from context or mark it `unspecified` so the worker asks before broad edits.
Generated work IDs are short pet-name IDs such as `amber-lantern`; the script appends a numeric suffix if needed.
If the argument is a single token and `~/.codex/isolate/requests/<token>` exists, treat it as `start <token>` instead of dispatching new work.

### Worker: `/isolate start <work_id>`

When the user invokes `/isolate start` with a generated work ID, start the saved request:

```zsh
~/skills/isolate/scripts/isolate-start.zsh --work-id <work_id>
```

Then `cd` into the printed worktree path, read `.codex/isolate/request.md`, read repo instructions, and continue from there. If the user pastes a full brief with repo/task/base/ownership fields, use `isolate-start.zsh --repo ... --task ...` directly.

### Finish: `/isolate finish <work_id>`

When the dispatcher invokes finish, trust the worker output and run:

```zsh
~/skills/isolate/scripts/isolate-finish.zsh --work-id <work_id>
```

Finish stages and commits worker changes, merges the worker branch into the source checkout's current branch, removes the clean worktree, prunes worktree metadata, deletes the merged worker branch, and marks the request completed. It refuses dirty source checkouts, missing workers, commit failures, and merge conflicts.

## Worker Contract

When invoked in a worker thread:

1. Read the saved request or pasted worker brief and repo `AGENTS.md`.
2. Start or enter the assigned worktree before editing files.
3. Run all commands and file edits from the isolated worktree path.
4. Do not edit the source checkout after isolation starts.
5. Keep to the assigned ownership scope. Ask before touching files outside it.
6. Check `.codex/isolate/inbox.md` at startup, before major edits, before tests, and before the final response.
7. Report changed paths, tests/checks run, remaining risks, branch, and worktree path.
8. Do not remove the worktree while it has uncommitted changes.

If the current thread is the dispatcher, do not implement the delegated work after creating the request.

## Startup

```zsh
~/skills/isolate/scripts/isolate-start.zsh --work-id <work_id>
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
