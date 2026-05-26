#!/usr/bin/env zsh
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  isolate-note.zsh [--worktree PATH] --message TEXT
  isolate-note.zsh [--worktree PATH] TEXT...

Options:
  --worktree PATH   Worktree whose inbox should receive the note. Defaults to the current directory.
  --message TEXT    Guidance to append.
  -h, --help        Show this help.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

worktree="$PWD"
message=""

while (( $# )); do
  case "$1" in
    --worktree)
      worktree="${2:-}"
      shift 2
      ;;
    --message)
      message="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      usage >&2
      fail "unknown argument: $1"
      ;;
    *)
      break
      ;;
  esac
done

if [[ -z "$message" && $# -gt 0 ]]; then
  message="$*"
fi

[[ -n "$message" ]] || fail "message is required"
[[ -d "$worktree" ]] || fail "worktree does not exist: $worktree"
if ! git -C "$worktree" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "not a Git worktree: $worktree"
fi

worktree=$(git -C "$worktree" rev-parse --show-toplevel)
worktree=$(cd "$worktree" && pwd -P)
inbox="$worktree/.codex/isolate/inbox.md"
mkdir -p "$worktree/.codex/isolate"

{
  printf '\n## %s\n\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '%s\n' "$message"
} >> "$inbox"

printf 'appended=%s\n' "$inbox"
