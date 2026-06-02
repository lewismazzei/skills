---
name: dispatch
description: Dispatch coding or research tasks to background worker agents in dedicated Git worktrees while the parent thread remains the control plane. Use when the user invokes /dispatch, asks to delegate work to a worker thread, wants pet-named workers, worker inbox/status tracking, or automatic cleanup prompts for worker worktrees.
---

# Dispatch

Use this skill as a lightweight agent orchestration control plane. The parent
thread creates and tracks pet-named workers; worker agents execute inside their
assigned Git worktrees.

## Control Commands

- `/dispatch <task>`: create a worker worktree, spawn a worker agent, record its
  agent id, and return control immediately.
- `/dispatch list`: refresh worker state and summarize active workers.
- `/dispatch status <pet-name>`: inspect one worker and surface queued notices.
- `/dispatch note <pet-name> <message>`: append to the worker inbox and, if an
  agent id is known, send a short live nudge to check the inbox.
- `/dispatch stop <pet-name>`: close the worker agent when possible, mark the
  worker cancelled, then inspect cleanup eligibility.
- `/dispatch cleanup <pet-name>`: inspect cleanup eligibility; ask before
  running destructive cleanup.

## Dispatch Workflow

1. Run `~/skills/dispatch/scripts/dispatch-watch.zsh --once`, then
   `~/skills/dispatch/scripts/dispatch-inbox.zsh`, and surface any unread
   parent notifications first.
2. For new work, infer the source Git repo from the current directory unless
   the user specifies one. Run `git status --short --branch` and note dirty or
   untracked paths before delegation.
3. Create the worker:

```zsh
~/skills/dispatch/scripts/dispatch-create.zsh --repo /path/to/repo --task "task" --owner "files or dirs"
```

4. Spawn a `worker` agent with the generated worktree path and the prompt in
   `templates/worker-prompt.md`. Workers are not alone in the codebase; they
   must not revert edits made by others and must report changed paths.
   If spawning fails, mark the worker failed and inspect cleanup eligibility.
5. Record the returned agent id:

```zsh
~/skills/dispatch/scripts/dispatch-state.zsh --worker <pet-name> --status running --agent-id <agent-id> --message "worker spawned"
```

6. Do not call `wait_agent` after dispatch unless the user explicitly asks to
   block. The parent remains available for normal conversation and more
   delegation.

## Worker Contract

Workers must work only inside their assigned worktree, respect the ownership
scope, check `.codex/dispatch/inbox.ndjson` at checkpoints, and write
`.codex/dispatch/result.md` before marking themselves ready:

```zsh
~/skills/dispatch/scripts/dispatch-state.zsh --worker <pet-name> --status ready --message "summary"
```

If blocked, use `--status blocked`. Workers do not clean up worktrees and do not
commit unless the parent explicitly asks.

## Cleanup

Cleanup is parent-owned. When a worker is ready, failed, cancelled, or otherwise
inactive, inspect cleanup:

```zsh
~/skills/dispatch/scripts/dispatch-cleanup.zsh --worker <pet-name>
```

Ask the user before deletion. Only after confirmation run the same command with
`--yes`. Cleanup refuses dirty worktrees and unmerged branches.

Cron may run `dispatch-watch.zsh --once` to queue parent notifications, but the
skill must still work without cron by refreshing opportunistically.
