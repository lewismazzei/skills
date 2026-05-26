#!/usr/bin/env zsh
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  isolate-dispatch.zsh [--repo PATH] (--task TEXT | TEXT...) [options]

Options:
  --repo PATH       Source Git repo. Defaults to nearest repo from cwd.
  --task TEXT       Work description for the worker.
  --base REF        Base ref for the worker branch. Defaults to HEAD.
  --branch NAME     Worker branch. Defaults to worker/<task-slug>.
  --owner TEXT      File/directory ownership scope.
  --avoid TEXT      Files/directories the worker must not touch.
  --acceptance TEXT Checks or behavior required before completion.
  --work-id ID      Explicit work ID. Defaults to timestamp plus slug.
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

write_field() {
  local path="$1"
  local value="$2"
  printf '%s\n' "$value" > "$path"
}

repo=""
task=""
base="HEAD"
branch=""
owner=""
avoid=""
acceptance=""
work_id=""
remaining=()

while (( $# )); do
  case "$1" in
    --repo)
      repo="${2:-}"
      shift 2
      ;;
    --task)
      task="${2:-}"
      shift 2
      ;;
    --base)
      base="${2:-}"
      shift 2
      ;;
    --branch)
      branch="${2:-}"
      shift 2
      ;;
    --owner)
      owner="${2:-}"
      shift 2
      ;;
    --avoid)
      avoid="${2:-}"
      shift 2
      ;;
    --acceptance)
      acceptance="${2:-}"
      shift 2
      ;;
    --work-id)
      work_id="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      remaining+=("$@")
      break
      ;;
    -*)
      usage >&2
      fail "unknown argument: $1"
      ;;
    *)
      remaining+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$task" && ${#remaining[@]} -gt 0 ]]; then
  task="${(j: :)remaining}"
fi

[[ -n "$task" ]] || fail "task is required"

if [[ -z "$repo" ]]; then
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    repo=$(git rev-parse --show-toplevel)
  else
    fail "--repo is required outside a Git repo"
  fi
fi

[[ -d "$repo" ]] || fail "repo does not exist: $repo"
if ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "not a Git worktree: $repo"
fi

repo=$(git -C "$repo" rev-parse --show-toplevel)
repo=$(cd "$repo" && pwd -P)

if ! git -C "$repo" rev-parse --verify --quiet "$base^{commit}" >/dev/null; then
  fail "base ref does not resolve to a commit: $base"
fi

task_slug=$(slugify "$task")
request_root="${CODEX_ISOLATE_REQUESTS_DIR:-$HOME/.codex/isolate/requests}"

if [[ -z "$work_id" ]]; then
  base_work_id="$(date -u +%Y%m%d%H%M%S)-$task_slug"
  work_id="$base_work_id"
  suffix=2
  while [[ -e "$request_root/$work_id" ]]; do
    work_id="$base_work_id-$suffix"
    suffix=$((suffix + 1))
  done
fi

if [[ -z "$branch" ]]; then
  branch="worker/$work_id"
fi

request_dir="$request_root/$work_id"
[[ ! -e "$request_dir" ]] || fail "request already exists: $request_dir"

created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
requester_cwd=$(pwd -P)
source_status=$(git -C "$repo" status --short --branch)

mkdir -p "$request_dir"
write_field "$request_dir/work_id" "$work_id"
write_field "$request_dir/created_at" "$created_at"
write_field "$request_dir/repo" "$repo"
write_field "$request_dir/base" "$base"
write_field "$request_dir/branch" "$branch"
write_field "$request_dir/task" "$task"
write_field "$request_dir/owner" "${owner:-unspecified}"
write_field "$request_dir/avoid" "${avoid:-unspecified}"
write_field "$request_dir/acceptance" "${acceptance:-unspecified}"
write_field "$request_dir/requester_cwd" "$requester_cwd"

{
  printf '# Isolate Work Request\n\n'
  printf -- '- work_id: %s\n' "$work_id"
  printf -- '- created_at: %s\n' "$created_at"
  printf -- '- repo: %s\n' "$repo"
  printf -- '- base: %s\n' "$base"
  printf -- '- branch: %s\n' "$branch"
  printf -- '- task: %s\n' "$task"
  printf -- '- ownership: %s\n' "${owner:-unspecified}"
  printf -- '- do_not_touch: %s\n' "${avoid:-unspecified}"
  printf -- '- acceptance: %s\n\n' "${acceptance:-unspecified}"
  printf '## Worker Prompt\n\n'
  printf '```text\n/isolate %s\n```\n\n' "$work_id"
  printf '## Source Checkout Status At Dispatch\n\n'
  printf '```text\n%s\n```\n' "$source_status"
} > "$request_dir/brief.md"

printf 'work_id=%s\n' "$work_id"
printf 'request_dir=%s\n' "$request_dir"
printf 'worker_prompt=/isolate %s\n' "$work_id"
printf 'repo=%s\n' "$repo"
printf 'branch=%s\n' "$branch"
printf 'brief=%s\n' "$request_dir/brief.md"
