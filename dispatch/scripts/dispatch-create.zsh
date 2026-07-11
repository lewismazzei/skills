#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:a:h}
. "$script_dir/dispatch-common.zsh"

usage() {
  cat <<'USAGE'
Usage:
  dispatch-create.zsh --task TEXT [--repo PATH] [options]

Options:
  --repo PATH       Source Git repository. Defaults to nearest repo from cwd.
  --task TEXT       Worker task.
  --owner TEXT      Files/directories this worker may edit.
  --avoid TEXT      Files/directories this worker must not touch.
  --base REF        Base commit/ref for the worker branch. Defaults to HEAD.
  --name NAME       Explicit pet name. Defaults to generated pet name.
  --worktree PATH   Explicit worktree path. Defaults to <repo-parent>/.worktrees/<repo-name>/<worker>.
  -h, --help        Show this help.
USAGE
}

repo=""
task=""
owner="unspecified"
avoid="unspecified"
base="HEAD"
name=""
worktree=""

while (( $# )); do
  case "$1" in
    --repo) repo="${2:-}"; shift 2 ;;
    --task) task="${2:-}"; shift 2 ;;
    --owner) owner="${2:-}"; shift 2 ;;
    --avoid) avoid="${2:-}"; shift 2 ;;
    --base) base="${2:-}"; shift 2 ;;
    --name) name="${2:-}"; shift 2 ;;
    --worktree) worktree="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; dispatch_fail "unknown argument: $1" ;;
  esac
done

[[ -n "$task" ]] || dispatch_fail "--task is required"

if [[ -z "$repo" ]]; then
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    repo=$(git rev-parse --show-toplevel)
  else
    dispatch_fail "--repo is required outside a Git repository"
  fi
fi

[[ -d "$repo" ]] || dispatch_fail "repo does not exist: $repo"
git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || dispatch_fail "not a Git repository: $repo"
repo=$(git -C "$repo" rev-parse --show-toplevel)
repo=$(cd "$repo" && pwd -P)
git -C "$repo" rev-parse --verify --quiet "$base^{commit}" >/dev/null || dispatch_fail "base ref does not resolve: $base"

root=$(dispatch_root)
mkdir -p "$root/workers" "$root/completed" "$root/control-plane"

if [[ -z "$name" ]]; then
  seed="$(dispatch_now)-$repo-$task"
  base_name=$(dispatch_pet_name "$seed")
  name="$base_name"
  suffix=2
  while [[ -e "$root/workers/$name" || -e "$root/completed/$name" ]]; do
    name="$base_name-$suffix"
    suffix=$((suffix + 1))
  done
else
  name=$(dispatch_slug "$name")
fi

branch="dispatch/$name"
if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
  dispatch_fail "branch already exists: $branch"
fi

if [[ -z "$worktree" ]]; then
  worktree=$(dispatch_default_worktree "$repo" "$name")
fi
[[ ! -e "$worktree" ]] || dispatch_fail "worktree path already exists: $worktree"

worker_dir="$root/workers/$name"
[[ ! -e "$worker_dir" ]] || dispatch_fail "worker already exists: $name"

source_status=$(git -C "$repo" status --short --branch)
created_at=$(dispatch_now)

git -C "$repo" worktree add -b "$branch" "$worktree" "$base" >/dev/null
worktree=$(cd "$worktree" && pwd -P)

mkdir -p "$worker_dir" "$worktree/.codex/dispatch"
dispatch_write "$worker_dir" name "$name"
dispatch_write "$worker_dir" status created
dispatch_write "$worker_dir" repo "$repo"
dispatch_write "$worker_dir" worktree "$worktree"
dispatch_write "$worker_dir" branch "$branch"
dispatch_write "$worker_dir" task "$task"
dispatch_write "$worker_dir" owner "$owner"
dispatch_write "$worker_dir" avoid "$avoid"
dispatch_write "$worker_dir" base "$base"
dispatch_write "$worker_dir" created_at "$created_at"
dispatch_write "$worker_dir" dirty unknown
dispatch_write "$worker_dir" branch_merged unknown
dispatch_write "$worker_dir" cleanup_ready no

printf '%s\n' "$source_status" > "$worker_dir/source-status-at-dispatch.txt"
touch "$worker_dir/inbox.ndjson" "$worker_dir/outbox.ndjson" "$worker_dir/events.ndjson"

{
  printf '# Dispatch Worker Request\n\n'
  printf -- '- worker: %s\n' "$name"
  printf -- '- task: %s\n' "$task"
  printf -- '- repo: %s\n' "$repo"
  printf -- '- worktree: %s\n' "$worktree"
  printf -- '- branch: %s\n' "$branch"
  printf -- '- base: %s\n' "$base"
  printf -- '- owner: %s\n' "$owner"
  printf -- '- avoid: %s\n\n' "$avoid"
  printf '## Source Status At Dispatch\n\n'
  printf '```text\n%s\n```\n' "$source_status"
} > "$worker_dir/request.md"

{
  printf '# Dispatch Worker Result\n\n'
  printf 'Status: pending\n\n'
  printf '## Acceptance Contract\n\n'
  printf -- '- Observable behavior: pending\n'
  printf -- '- Given/When/Then acceptance example: pending\n\n'
  printf '## Proof Matrix\n\n'
  printf '| Contract / Symptom | Evidence | Result |\n'
  printf '| --- | --- | --- |\n'
  printf '| pending | pending | pending |\n\n'
  printf '## Production / Default Config Coverage\n\n'
  printf -- '- pending\n\n'
  printf '## Quality Gates\n\n'
  printf -- '- Symptom or acceptance proof: pending\n'
  printf -- '- Lint/type/build: pending\n'
  printf -- '- Complexity/mutation/hardening: pending\n'
  printf -- '- E2E/manual QA: pending\n\n'
  printf '## Cleanup / Architecture Review\n\n'
  printf -- '- pending\n\n'
  printf '## Changed Paths\n\n'
  printf -- '- pending\n\n'
  printf '## Commands / Checks Run\n\n'
  printf -- '- pending\n\n'
  printf '## Risks / Conflicts\n\n'
  printf -- '- pending\n\n'
  printf '## Remaining Work\n\n'
  printf -- '- pending\n'
} > "$worker_dir/result.md"

ln -s "$worker_dir/request.md" "$worktree/.codex/dispatch/request.md"
ln -s "$worker_dir/inbox.ndjson" "$worktree/.codex/dispatch/inbox.ndjson"
ln -s "$worker_dir/outbox.ndjson" "$worktree/.codex/dispatch/outbox.ndjson"
ln -s "$worker_dir/result.md" "$worktree/.codex/dispatch/result.md"
ln -s "$worker_dir/state.json" "$worktree/.codex/dispatch/state.json"
printf '%s\n' "$worker_dir" > "$worktree/.codex/dispatch/worker-dir"

exclude_file=$(git -C "$worktree" rev-parse --git-path info/exclude)
mkdir -p "$(dirname "$exclude_file")"
touch "$exclude_file"
if ! grep -Fxq '.codex/dispatch/' "$exclude_file"; then
  printf '\n# dispatch worker metadata\n.codex/dispatch/\n' >> "$exclude_file"
fi

dispatch_event "$worker_dir" created "worker worktree created"
dispatch_write_state "$worker_dir"

printf 'name=%s\n' "$name"
printf 'worker_dir=%s\n' "$worker_dir"
printf 'worktree=%s\n' "$worktree"
printf 'branch=%s\n' "$branch"
printf 'request=%s\n' "$worker_dir/request.md"
printf 'state=%s\n' "$worker_dir/state.json"
