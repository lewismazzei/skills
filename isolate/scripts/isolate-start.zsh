#!/usr/bin/env zsh
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  isolate-start.zsh --repo PATH (--task TEXT | --branch NAME) [options]
  isolate-start.zsh --work-id ID [options]

Options:
  --work-id ID     Load a request from ~/.codex/isolate/requests/ID.
  --repo PATH       Source Git repo to isolate from.
  --task TEXT       Short task name. Used to derive branch/worktree names.
  --branch NAME     Branch to create for the worker.
  --base REF        Base ref for the worktree branch. Defaults to HEAD.
  --worktree PATH   Explicit worktree path. Defaults to a sibling directory.
  --owner TEXT      File/directory ownership scope for the worker.
  -h, --help        Show this help.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

slugify() {
  local input="$1"
  local slug
  slug=$(printf '%s' "$input" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g' | cut -c 1-64)
  if [[ -z "$slug" ]]; then
    slug="worker-$(date -u +%Y%m%d%H%M%S)"
  fi
  printf '%s' "$slug"
}

repo=""
task=""
branch=""
base="HEAD"
worktree=""
owner=""
avoid=""
acceptance=""
work_id=""
request_dir=""

read_request_field() {
  local name="$1"
  local file="$request_dir/$name"
  if [[ -f "$file" ]]; then
    cat "$file"
  fi
}

while (( $# )); do
  case "$1" in
    --work-id)
      work_id="${2:-}"
      shift 2
      ;;
    --repo)
      repo="${2:-}"
      shift 2
      ;;
    --task)
      task="${2:-}"
      shift 2
      ;;
    --branch)
      branch="${2:-}"
      shift 2
      ;;
    --base)
      base="${2:-}"
      shift 2
      ;;
    --worktree)
      worktree="${2:-}"
      shift 2
      ;;
    --owner)
      owner="${2:-}"
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

if [[ -n "$work_id" ]]; then
  request_root="${CODEX_ISOLATE_REQUESTS_DIR:-$HOME/.codex/isolate/requests}"
  request_dir="$request_root/$work_id"
  [[ -d "$request_dir" ]] || fail "isolate request not found: $request_dir"

  [[ -n "$repo" ]] || repo=$(read_request_field repo)
  [[ -n "$task" ]] || task=$(read_request_field task)
  [[ -n "$branch" ]] || branch=$(read_request_field branch)
  if [[ "$base" == "HEAD" ]]; then
    saved_base=$(read_request_field base)
    [[ -n "$saved_base" ]] && base="$saved_base"
  fi
  [[ -n "$owner" ]] || owner=$(read_request_field owner)
  avoid=$(read_request_field avoid)
  acceptance=$(read_request_field acceptance)
fi

[[ -n "$repo" ]] || fail "--repo is required"
[[ -d "$repo" ]] || fail "repo does not exist: $repo"

if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "not a Git worktree: $repo"
fi

repo=$(git -C "$repo" rev-parse --show-toplevel)
repo=$(cd "$repo" && pwd -P)

[[ -n "$task" || -n "$branch" ]] || fail "provide --task or --branch"

if [[ -z "$branch" ]]; then
  branch="worker/$(slugify "$task")"
fi

branch_slug=$(slugify "$branch")

if [[ -z "$worktree" ]]; then
  worktree="$(dirname "$repo")/$(basename "$repo")-$branch_slug"
fi

[[ ! -e "$worktree" ]] || fail "worktree path already exists: $worktree"

if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
  fail "branch already exists: $branch"
fi

if ! git -C "$repo" rev-parse --verify --quiet "$base^{commit}" >/dev/null; then
  fail "base ref does not resolve to a commit: $base"
fi

source_status=$(git -C "$repo" status --short --branch)
created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

git -C "$repo" worktree add -b "$branch" "$worktree" "$base"
worktree=$(cd "$worktree" && pwd -P)

mkdir -p "$worktree/.codex/isolate"
exclude_file=$(git -C "$worktree" rev-parse --git-path info/exclude)
mkdir -p "$(dirname "$exclude_file")"
touch "$exclude_file"
if ! grep -Fxq '.codex/isolate/' "$exclude_file"; then
  printf '\n# isolate worker metadata\n.codex/isolate/\n' >> "$exclude_file"
fi

{
  printf '# Isolate Worker Metadata\n\n'
  printf -- '- created_at: %s\n' "$created_at"
  printf -- '- work_id: %s\n' "${work_id:-none}"
  printf -- '- request_dir: %s\n' "${request_dir:-none}"
  printf -- '- source_repo: %s\n' "$repo"
  printf -- '- worktree: %s\n' "$worktree"
  printf -- '- branch: %s\n' "$branch"
  printf -- '- base: %s\n' "$base"
  printf -- '- owner: %s\n' "${owner:-unspecified}"
  printf -- '- do_not_touch: %s\n' "${avoid:-unspecified}"
  printf -- '- main_thread_verification: %s\n' "${acceptance:-unspecified}"
  printf -- '- task: %s\n\n' "${task:-unspecified}"
  printf '## Source Checkout Status At Startup\n\n'
  printf '```text\n%s\n```\n' "$source_status"
} > "$worktree/.codex/isolate/README.md"

if [[ -n "$request_dir" && -f "$request_dir/brief.md" ]]; then
  cp "$request_dir/brief.md" "$worktree/.codex/isolate/request.md"
fi

if [[ -n "$request_dir" ]]; then
  printf '%s\n' "$worktree" > "$request_dir/worktree"
  printf '%s\n' "$created_at" > "$request_dir/started_at"
fi

{
  printf '# Isolate Inbox\n\n'
  printf 'Created: %s\n\n' "$created_at"
  printf 'Parent threads may append guidance here with isolate-note.zsh. Workers should check this file at checkpoints.\n'
} > "$worktree/.codex/isolate/inbox.md"

printf 'worktree=%s\n' "$worktree"
printf 'branch=%s\n' "$branch"
printf 'base=%s\n' "$base"
printf 'metadata=%s\n' "$worktree/.codex/isolate/README.md"
printf 'inbox=%s\n' "$worktree/.codex/isolate/inbox.md"
