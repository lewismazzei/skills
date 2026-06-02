#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:a:h}
. "$script_dir/dispatch-common.zsh"

usage() {
  cat <<'USAGE'
Usage:
  dispatch-cleanup.zsh --worker NAME [--yes]

Inspect or perform safe cleanup. Destructive cleanup requires --yes and refuses
dirty worktrees or unmerged branches.
USAGE
}

worker=""
yes=0

while (( $# )); do
  case "$1" in
    --worker) worker="${2:-}"; shift 2 ;;
    --yes) yes=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; dispatch_fail "unknown argument: $1" ;;
  esac
done

[[ -n "$worker" ]] || dispatch_fail "--worker is required"
root=$(dispatch_root)
worker_dir="$root/workers/$worker"
[[ -d "$worker_dir" ]] || dispatch_fail "unknown worker: $worker"

repo=$(dispatch_read "$worker_dir" repo)
worktree=$(dispatch_read "$worker_dir" worktree)
branch=$(dispatch_read "$worker_dir" branch)

[[ -n "$repo" && -d "$repo" ]] || dispatch_fail "repo missing: $repo"
git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || dispatch_fail "not a Git repository: $repo"

dirty="unknown"
if [[ -n "$worktree" && -d "$worktree" ]] && git -C "$worktree" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [[ -n "$(git -C "$worktree" status --porcelain)" ]]; then
    dirty="yes"
  else
    dirty="no"
  fi
else
  dirty="missing"
fi

branch_merged="missing"
if [[ -n "$branch" ]] && git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
  if git -C "$repo" merge-base --is-ancestor "$branch" HEAD >/dev/null 2>&1; then
    branch_merged="yes"
  else
    branch_merged="no"
  fi
fi

dispatch_write "$worker_dir" dirty "$dirty"
dispatch_write "$worker_dir" branch_merged "$branch_merged"

ready="no"
reason=""
if [[ "$dirty" != "no" && "$dirty" != "missing" ]]; then
  reason="worktree has uncommitted changes"
elif [[ "$branch_merged" == "no" ]]; then
  reason="worker branch is not merged into the source checkout HEAD"
else
  ready="yes"
  reason="worktree is clean and branch is merged or missing"
fi
dispatch_write "$worker_dir" cleanup_ready "$ready"
dispatch_write_state "$worker_dir"

printf 'worker=%s\n' "$worker"
printf 'worktree=%s\n' "$worktree"
printf 'branch=%s\n' "$branch"
printf 'dirty=%s\n' "$dirty"
printf 'branch_merged=%s\n' "$branch_merged"
printf 'cleanup_ready=%s\n' "$ready"
printf 'reason=%s\n' "$reason"

if (( yes == 0 )); then
  if [[ "$ready" == "yes" ]]; then
    printf 'confirmation_required=yes\n'
    printf 'cleanup_command=%s --worker %s --yes\n' "$0" "$worker"
  fi
  exit 0
fi

[[ "$ready" == "yes" ]] || dispatch_fail "cleanup refused: $reason"

removed_worktree="no"
deleted_branch="no"
if [[ "$dirty" != "missing" && -d "$worktree" ]]; then
  git -C "$repo" worktree remove "$worktree"
  git -C "$repo" worktree prune
  removed_worktree="yes"
fi

if [[ "$branch_merged" == "yes" ]]; then
  git -C "$repo" branch -d "$branch" >/dev/null
  deleted_branch="yes"
fi

finished_at=$(dispatch_now)
{
  printf '# Dispatch Cleanup\n\n'
  printf -- '- worker: %s\n' "$worker"
  printf -- '- cleaned_at: %s\n' "$finished_at"
  printf -- '- removed_worktree: %s\n' "$removed_worktree"
  printf -- '- deleted_branch: %s\n' "$deleted_branch"
  printf -- '- reason: %s\n' "$reason"
} > "$worker_dir/cleanup.md"
dispatch_write "$worker_dir" status cleaned
dispatch_event "$worker_dir" cleaned "cleanup completed"
dispatch_write_state "$worker_dir"

completed_dir="$root/completed/$worker"
if [[ -e "$completed_dir" ]]; then
  completed_dir="$root/completed/$worker-$(date -u +%Y%m%d%H%M%S)"
fi
mkdir -p "$root/completed"
mv "$worker_dir" "$completed_dir"

printf 'removed_worktree=%s\n' "$removed_worktree"
printf 'deleted_branch=%s\n' "$deleted_branch"
printf 'completed_dir=%s\n' "$completed_dir"
