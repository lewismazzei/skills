#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:a:h}
. "$script_dir/dispatch-common.zsh"
setopt null_glob

usage() {
  cat <<'USAGE'
Usage:
  dispatch-watch.zsh --once

Poll worker state and queue deduplicated parent notifications.
USAGE
}

once=0
while (( $# )); do
  case "$1" in
    --once) once=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; dispatch_fail "unknown argument: $1" ;;
  esac
done

(( once == 1 )) || dispatch_fail "only --once is supported"

root=$(dispatch_root)
workers_dir="$root/workers"
control_dir="$root/control-plane"
mkdir -p "$workers_dir" "$control_dir"

lock_dir="$root/.watch.lock"
if ! mkdir "$lock_dir" 2>/dev/null; then
  old_pid=""
  [[ -f "$lock_dir/pid" ]] && old_pid=$(cat "$lock_dir/pid")
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    printf 'watcher already running\n'
    exit 0
  fi
  rm -rf "$lock_dir"
  if ! mkdir "$lock_dir" 2>/dev/null; then
    printf 'watcher already running\n'
    exit 0
  fi
fi
printf '%s\n' "$$" > "$lock_dir/pid"
trap 'rm -f "$lock_dir/pid" 2>/dev/null || true; rmdir "$lock_dir" 2>/dev/null || true' EXIT

sent_file="$control_dir/sent.keys"
touch "$sent_file" "$control_dir/inbox.ndjson"
notifications=0

queue_notice() {
  local key="$1"
  local worker="$2"
  local type="$3"
  local message="$4"
  local now
  if grep -Fxq "$key" "$sent_file"; then
    return 0
  fi
  now=$(dispatch_now)
  {
    printf '{"time":'
    dispatch_json_string "$now"
    printf ',"worker":'
    dispatch_json_string "$worker"
    printf ',"type":'
    dispatch_json_string "$type"
    printf ',"message":'
    dispatch_json_string "$message"
    printf '}\n'
  } >> "$control_dir/inbox.ndjson"
  printf '%s\n' "$key" >> "$sent_file"
  notifications=$((notifications + 1))
}

for worker_dir in "$workers_dir"/*; do
  [[ -d "$worker_dir" ]] || continue
  name=$(dispatch_read "$worker_dir" name)
  worker_status=$(dispatch_read "$worker_dir" status)
  repo=$(dispatch_read "$worker_dir" repo)
  worktree=$(dispatch_read "$worker_dir" worktree)
  branch=$(dispatch_read "$worker_dir" branch)

  dirty="unknown"
  if [[ -n "$worktree" && -d "$worktree" ]] && git -C "$worktree" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [[ -n "$(git -C "$worktree" status --porcelain)" ]]; then
      dirty="yes"
    else
      dirty="no"
    fi
  fi
  dispatch_write "$worker_dir" dirty "$dirty"

  branch_merged="unknown"
  if [[ -n "$repo" && -d "$repo" && -n "$branch" ]] && git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
      if git -C "$repo" merge-base --is-ancestor "$branch" HEAD >/dev/null 2>&1; then
        branch_merged="yes"
      else
        branch_merged="no"
      fi
    else
      branch_merged="missing"
    fi
  fi
  dispatch_write "$worker_dir" branch_merged "$branch_merged"

  cleanup_ready="no"
  if [[ "$dirty" == "no" && ( "$branch_merged" == "yes" || "$branch_merged" == "missing" ) ]]; then
    cleanup_ready="yes"
  fi
  dispatch_write "$worker_dir" cleanup_ready "$cleanup_ready"
  dispatch_write_state "$worker_dir"

  case "$worker_status" in
    blocked)
      queue_notice "$name:blocked" "$name" blocked "worker is blocked; inspect outbox/result"
      ;;
    ready)
      queue_notice "$name:ready" "$name" ready "worker marked ready; review result and worktree diff"
      ;;
    failed)
      queue_notice "$name:failed" "$name" failed "worker marked failed; inspect result and cleanup eligibility"
      ;;
    cancelled)
      queue_notice "$name:cancelled" "$name" cancelled "worker is cancelled; inspect cleanup eligibility"
      ;;
    integrated)
      queue_notice "$name:integrated" "$name" integrated "worker marked integrated; cleanup may be possible"
      ;;
  esac

  if [[ "$cleanup_ready" == "yes" ]]; then
    queue_notice "$name:cleanup-ready" "$name" cleanup_ready "worktree is clean and branch is merged or missing; confirm cleanup before deletion"
  fi
done

printf 'notifications=%s\n' "$notifications"
printf 'control_inbox=%s\n' "$control_dir/inbox.ndjson"
