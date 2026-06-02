#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:a:h}
. "$script_dir/dispatch-common.zsh"

usage() {
  cat <<'USAGE'
Usage:
  dispatch-note.zsh --worker NAME --message TEXT

Append a parent note to the worker inbox.
USAGE
}

worker=""
message=""

while (( $# )); do
  case "$1" in
    --worker) worker="${2:-}"; shift 2 ;;
    --message) message="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; dispatch_fail "unknown argument: $1" ;;
  esac
done

[[ -n "$worker" ]] || dispatch_fail "--worker is required"
[[ -n "$message" ]] || dispatch_fail "--message is required"
worker_dir=$(dispatch_worker_dir "$worker")
[[ -d "$worker_dir" ]] || dispatch_fail "unknown worker: $worker"

dispatch_event "$worker_dir" parent_note "$message" inbox.ndjson
dispatch_event "$worker_dir" parent_note "$message"
dispatch_write "$worker_dir" last_parent_note_at "$(dispatch_now)"
dispatch_write_state "$worker_dir"

printf 'worker=%s\n' "$worker"
printf 'inbox=%s\n' "$worker_dir/inbox.ndjson"
