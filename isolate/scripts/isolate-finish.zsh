#!/usr/bin/env zsh
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  isolate-finish.zsh --work-id ID [options]

Options:
  --work-id ID      Isolate work request to finish.
  --message TEXT    Commit message for worker changes.
  --keep-branch     Do not delete the merged worker branch.
  --keep-request    Do not move the request to completed/.
  -h, --help        Show this help.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

read_field() {
  local name="$1"
  local file="$request_dir/$name"
  if [[ -f "$file" ]]; then
    cat "$file"
  fi
}

slugify() {
  local input="$1"
  local slug
  slug=$(printf '%s' "$input" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g' | cut -c 1-64)
  [[ -n "$slug" ]] || slug="worker"
  printf '%s' "$slug"
}

commit_message_for_task() {
  local task="$1"
  local summary
  local lower
  local type

  summary=$(printf '%s' "$task" | tr '\n' ' ' | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//')
  [[ -n "$summary" ]] || summary="finish isolated worker"
  lower=$(printf '%s' "$summary" | tr '[:upper:]' '[:lower:]')

  case "$lower" in
    fix*|repair*|restore*|bug*) type="fix" ;;
    add*|create*|implement*|build*|support*|enable*) type="feat" ;;
    document*|docs*) type="docs" ;;
    test*) type="test" ;;
    refactor*) type="refactor" ;;
    *) type="chore" ;;
  esac

  summary=$(printf '%s' "$summary" | cut -c 1-64)
  printf '%s: %s' "$type" "$summary"
}

find_worktree_for_branch() {
  local search_branch="$1"
  local current_path=""
  local line

  while IFS= read -r line; do
    case "$line" in
      worktree\ *)
        current_path="${line#worktree }"
        ;;
      branch\ refs/heads/*)
        if [[ "${line#branch refs/heads/}" == "$search_branch" ]]; then
          printf '%s' "$current_path"
          return 0
        fi
        ;;
    esac
  done < <(git -C "$repo" worktree list --porcelain)

  return 1
}

work_id=""
message=""
keep_branch=0
keep_request=0

while (( $# )); do
  case "$1" in
    --work-id)
      work_id="${2:-}"
      shift 2
      ;;
    --message)
      message="${2:-}"
      shift 2
      ;;
    --keep-branch)
      keep_branch=1
      shift
      ;;
    --keep-request)
      keep_request=1
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

[[ -n "$work_id" ]] || fail "--work-id is required"

request_root="${CODEX_ISOLATE_REQUESTS_DIR:-$HOME/.codex/isolate/requests}"
completed_root="${CODEX_ISOLATE_COMPLETED_DIR:-$HOME/.codex/isolate/completed}"
request_dir="$request_root/$work_id"
[[ -d "$request_dir" ]] || fail "isolate request not found: $request_dir"

repo=$(read_field repo)
branch=$(read_field branch)
task=$(read_field task)
worktree=$(read_field worktree)

[[ -n "$repo" ]] || fail "request is missing repo"
[[ -n "$branch" ]] || fail "request is missing branch"
[[ -d "$repo" ]] || fail "repo does not exist: $repo"

if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "not a Git worktree: $repo"
fi

repo=$(git -C "$repo" rev-parse --show-toplevel)
repo=$(cd "$repo" && pwd -P)

if [[ -z "$worktree" || ! -d "$worktree" ]]; then
  if found_worktree=$(find_worktree_for_branch "$branch"); then
    worktree="$found_worktree"
  fi
fi

if ! git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
  fail "worker branch does not exist: $branch"
fi

target_branch=$(git -C "$repo" branch --show-current)
[[ -n "$target_branch" ]] || fail "source checkout is detached"
[[ "$target_branch" != "$branch" ]] || fail "source checkout is on worker branch: $branch"

if [[ -n "$(git -C "$repo" status --porcelain)" ]]; then
  git -C "$repo" status --short --branch >&2
  fail "source checkout must be clean before finish"
fi

if [[ -d "$worktree" ]]; then
  worktree=$(git -C "$worktree" rev-parse --show-toplevel)
  worktree=$(cd "$worktree" && pwd -P)
  worker_branch=$(git -C "$worktree" branch --show-current)
  [[ "$worker_branch" == "$branch" ]] || fail "worktree is on '$worker_branch', expected '$branch'"

  git -C "$worktree" add -A
  if [[ -n "$(git -C "$worktree" status --porcelain)" ]]; then
    [[ -n "$message" ]] || message=$(commit_message_for_task "$task")
    git -C "$worktree" commit -m "$message"
  fi

  if [[ -n "$(git -C "$worktree" status --porcelain)" ]]; then
    git -C "$worktree" status --short --branch >&2
    fail "worker worktree is still dirty after commit"
  fi
else
  fail "worker worktree not found for branch: $branch"
fi

worker_head=$(git -C "$repo" rev-parse --short "$branch")

if ! git -C "$repo" merge --no-edit "$branch"; then
  git -C "$repo" merge --abort >/dev/null 2>&1 || true
  fail "merge failed; source checkout restored if Git allowed abort"
fi

if [[ -d "$worktree" ]]; then
  git -C "$repo" worktree remove "$worktree"
  git -C "$repo" worktree prune
fi

if (( ! keep_branch )); then
  git -C "$repo" branch -d "$branch"
fi

finished_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
printf '%s\n' "$finished_at" > "$request_dir/finished_at"
printf '%s\n' "$target_branch" > "$request_dir/target_branch"
printf '%s\n' "$worker_head" > "$request_dir/worker_head"
printf '%s\n' "$(git -C "$repo" rev-parse --short HEAD)" > "$request_dir/merged_head"

completed_dir=""
if (( ! keep_request )); then
  mkdir -p "$completed_root"
  completed_dir="$completed_root/$work_id"
  [[ ! -e "$completed_dir" ]] || completed_dir="$completed_root/$work_id-$(date -u +%Y%m%d%H%M%S)"
  mv "$request_dir" "$completed_dir"
fi

printf 'finished=%s\n' "$work_id"
printf 'repo=%s\n' "$repo"
printf 'target_branch=%s\n' "$target_branch"
printf 'merged_head=%s\n' "$(git -C "$repo" rev-parse --short HEAD)"
printf 'worker_branch=%s\n' "$branch"
if (( keep_branch )); then
  printf 'branch_retained=%s\n' "$branch"
else
  printf 'branch_deleted=%s\n' "$branch"
fi
if [[ -n "$completed_dir" ]]; then
  printf 'request_completed=%s\n' "$completed_dir"
else
  printf 'request_retained=%s\n' "$request_dir"
fi
