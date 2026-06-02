#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:a:h}
. "$script_dir/dispatch-common.zsh"

usage() {
  cat <<'USAGE'
Usage:
  dispatch-state.zsh --worker NAME [options]

Options:
  --status STATUS   Set worker status.
  --agent-id ID     Record spawned agent id.
  --message TEXT    Append a worker event/outbox message.
  -h, --help        Show this help.
USAGE
}

worker=""
worker_status=""
agent_id=""
message=""

while (( $# )); do
  case "$1" in
    --worker) worker="${2:-}"; shift 2 ;;
    --status) worker_status="${2:-}"; shift 2 ;;
    --agent-id) agent_id="${2:-}"; shift 2 ;;
    --message) message="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; dispatch_fail "unknown argument: $1" ;;
  esac
done

[[ -n "$worker" ]] || dispatch_fail "--worker is required"
worker_dir=$(dispatch_worker_dir "$worker")
[[ -d "$worker_dir" ]] || dispatch_fail "unknown worker: $worker"

if [[ -n "$worker_status" ]]; then
  dispatch_write "$worker_dir" status "$worker_status"
fi
if [[ -n "$agent_id" ]]; then
  dispatch_write "$worker_dir" agent_id "$agent_id"
fi
if [[ -n "$message" ]]; then
  dispatch_event "$worker_dir" "${worker_status:-message}" "$message" outbox.ndjson
  dispatch_event "$worker_dir" "${worker_status:-message}" "$message"
fi

dispatch_write_state "$worker_dir"

printf 'worker=%s\n' "$worker"
printf 'status=%s\n' "$(dispatch_read "$worker_dir" status)"
printf 'state=%s\n' "$worker_dir/state.json"
