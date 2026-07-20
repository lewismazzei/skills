#!/usr/bin/env zsh

dispatch_fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

dispatch_root() {
  printf '%s\n' "${CODEX_DISPATCH_HOME:-$HOME/.codex/dispatch}"
}

dispatch_default_worktree() {
  local repo="$1"
  local name="$2"
  local repo_parent="${repo:h}"
  local repo_name="${repo:t}"
  local worktree_root="${CODEX_DISPATCH_WORKTREE_ROOT:-$repo_parent/.worktrees}"
  printf '%s/%s/%s\n' "$worktree_root" "$repo_name" "$name"
}

dispatch_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

dispatch_slug() {
  local input="${1:-}"
  local slug
  slug=$(printf '%s' "$input" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g' | cut -c 1-72)
  [[ -n "$slug" ]] || slug="dispatch"
  printf '%s\n' "$slug"
}

dispatch_json_string() {
  local value="${1-}"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  value=${value//$'\t'/\\t}
  printf '"%s"' "$value"
}

dispatch_read() {
  local dir="$1"
  local field="$2"
  local file="$dir/$field"
  if [[ -f "$file" ]]; then
    cat "$file"
  fi
  return 0
}

dispatch_write() {
  local dir="$1"
  local field="$2"
  local value="${3-}"
  mkdir -p "$dir"
  printf '%s\n' "$value" > "$dir/$field"
}

dispatch_event() {
  local dir="$1"
  local type="$2"
  local message="${3-}"
  local file="${4:-events.ndjson}"
  local now
  now=$(dispatch_now)
  mkdir -p "$dir"
  {
    printf '{"time":'
    dispatch_json_string "$now"
    printf ',"type":'
    dispatch_json_string "$type"
    printf ',"message":'
    dispatch_json_string "$message"
    printf '}\n'
  } >> "$dir/$file"
}

dispatch_pet_name() {
  local seed_input="${1:-dispatch}"
  local offset="${2:-0}"
  local seed
  local adjectives=(amber brisk calm cedar clear clever copper crisp deft eager gentle golden honest lucid lucky mellow nimble quiet rapid steady tidy vivid warm wise)
  local nouns=(anchor atlas beacon bridge canyon comet compass harbor lantern maple meadow mint orbit pebble pixel quartz ribbon summit valley velvet vista willow)
  seed=$(printf '%s' "$seed_input" | cksum | awk '{print $1}')
  local index=$(((seed + offset) % (${#adjectives[@]} * ${#nouns[@]})))
  printf '%s-%s\n' "$adjectives[$((index % ${#adjectives[@]} + 1))]" "$nouns[$((index / ${#adjectives[@]} + 1))]"
}

dispatch_allocate_pet_name() {
  local seed_input="$1"
  local root="$2"
  local offset candidate
  local total=$((24 * 22))
  for (( offset = 0; offset < total; offset++ )); do
    candidate=$(dispatch_pet_name "$seed_input" "$offset")
    if [[ ! -e "$root/workers/$candidate" && ! -e "$root/completed/$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  dispatch_fail "pet-name namespace exhausted; refusing a numbered suffix"
}

dispatch_worker_dir() {
  local name="$1"
  printf '%s/workers/%s\n' "$(dispatch_root)" "$name"
}

dispatch_write_state() {
  local dir="$1"
  local name worker_status repo worktree branch task owner avoid agent_id display_name thread_name_error created_at updated_at dirty branch_merged cleanup_ready
  name=$(dispatch_read "$dir" name)
  worker_status=$(dispatch_read "$dir" status)
  repo=$(dispatch_read "$dir" repo)
  worktree=$(dispatch_read "$dir" worktree)
  branch=$(dispatch_read "$dir" branch)
  task=$(dispatch_read "$dir" task)
  owner=$(dispatch_read "$dir" owner)
  avoid=$(dispatch_read "$dir" avoid)
  agent_id=$(dispatch_read "$dir" agent_id)
  display_name=$(dispatch_read "$dir" display_name)
  thread_name_error=$(dispatch_read "$dir" thread_name_error)
  created_at=$(dispatch_read "$dir" created_at)
  dirty=$(dispatch_read "$dir" dirty)
  branch_merged=$(dispatch_read "$dir" branch_merged)
  cleanup_ready=$(dispatch_read "$dir" cleanup_ready)
  updated_at=$(dispatch_now)
  dispatch_write "$dir" updated_at "$updated_at"

  {
    printf '{\n'
    printf '  "name": %s,\n' "$(dispatch_json_string "$name")"
    printf '  "status": %s,\n' "$(dispatch_json_string "$worker_status")"
    printf '  "repo": %s,\n' "$(dispatch_json_string "$repo")"
    printf '  "worktree": %s,\n' "$(dispatch_json_string "$worktree")"
    printf '  "branch": %s,\n' "$(dispatch_json_string "$branch")"
    printf '  "task": %s,\n' "$(dispatch_json_string "$task")"
    printf '  "owner": %s,\n' "$(dispatch_json_string "$owner")"
    printf '  "avoid": %s,\n' "$(dispatch_json_string "$avoid")"
    printf '  "agent_id": %s,\n' "$(dispatch_json_string "$agent_id")"
    printf '  "display_name": %s,\n' "$(dispatch_json_string "$display_name")"
    printf '  "thread_name_error": %s,\n' "$(dispatch_json_string "$thread_name_error")"
    printf '  "created_at": %s,\n' "$(dispatch_json_string "$created_at")"
    printf '  "updated_at": %s,\n' "$(dispatch_json_string "$updated_at")"
    printf '  "dirty": %s,\n' "$(dispatch_json_string "$dirty")"
    printf '  "branch_merged": %s,\n' "$(dispatch_json_string "$branch_merged")"
    printf '  "cleanup_ready": %s\n' "$(dispatch_json_string "$cleanup_ready")"
    printf '}\n'
  } > "$dir/state.json"
}
