#!/usr/bin/env zsh
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  isolate-teardown.zsh --worktree PATH [--no-prune]

Options:
  --worktree PATH   Clean linked worktree to remove.
  --no-prune        Skip `git worktree prune` after removal.
  -h, --help        Show this help.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

worktree=""
prune=1

while (( $# )); do
  case "$1" in
    --worktree)
      worktree="${2:-}"
      shift 2
      ;;
    --no-prune)
      prune=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "unknown argument: $1"
      ;;
  esac
done

[[ -n "$worktree" ]] || fail "--worktree is required"
[[ -d "$worktree" ]] || fail "worktree does not exist: $worktree"
if ! git -C "$worktree" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "not a Git worktree: $worktree"
fi

worktree=$(git -C "$worktree" rev-parse --show-toplevel)
worktree=$(cd "$worktree" && pwd -P)

if [[ -d "$worktree/.git" ]]; then
  fail "refusing to remove primary checkout with .git directory: $worktree"
fi

dirty=$(git -C "$worktree" status --porcelain)
if [[ -n "$dirty" ]]; then
  printf 'ERROR: refusing to remove dirty worktree: %s\n\n' "$worktree" >&2
  git -C "$worktree" status --short --branch >&2
  exit 1
fi

common_git_dir=$(git -C "$worktree" rev-parse --path-format=absolute --git-common-dir)
branch=$(git -C "$worktree" branch --show-current || true)

git --git-dir="$common_git_dir" worktree remove "$worktree"

if (( prune )); then
  git --git-dir="$common_git_dir" worktree prune
fi

printf 'removed=%s\n' "$worktree"
if [[ -n "$branch" ]]; then
  printf 'branch_retained=%s\n' "$branch"
fi
