#!/usr/bin/env zsh
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  isolate-status.zsh [--worktree PATH]

Options:
  --worktree PATH   Worktree to inspect. Defaults to the current directory.
  -h, --help        Show this help.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

worktree="$PWD"

while (( $# )); do
  case "$1" in
    --worktree)
      worktree="${2:-}"
      shift 2
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

[[ -d "$worktree" ]] || fail "worktree does not exist: $worktree"
if ! git -C "$worktree" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "not a Git worktree: $worktree"
fi

worktree=$(git -C "$worktree" rev-parse --show-toplevel)
worktree=$(cd "$worktree" && pwd -P)
branch=$(git -C "$worktree" branch --show-current || true)
head=$(git -C "$worktree" rev-parse --short HEAD)

printf 'worktree: %s\n' "$worktree"
printf 'branch: %s\n' "${branch:-detached}"
printf 'head: %s\n\n' "$head"

printf 'status:\n'
git_status=$(git -C "$worktree" status --short --branch)
if [[ -n "$git_status" ]]; then
  printf '%s\n' "$git_status"
else
  printf 'clean\n'
fi

printf '\ndiff-stat:\n'
diff_stat=$(git -C "$worktree" diff --stat)
if [[ -n "$diff_stat" ]]; then
  printf '%s\n' "$diff_stat"
else
  printf 'no tracked diff\n'
fi

if [[ -f "$worktree/.codex/isolate/README.md" ]]; then
  printf '\nmetadata: %s\n' "$worktree/.codex/isolate/README.md"
fi

if [[ -f "$worktree/.codex/isolate/inbox.md" ]]; then
  printf 'inbox: %s\n' "$worktree/.codex/isolate/inbox.md"
fi
