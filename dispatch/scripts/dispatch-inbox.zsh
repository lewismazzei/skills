#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:a:h}
. "$script_dir/dispatch-common.zsh"

usage() {
  cat <<'USAGE'
Usage:
  dispatch-inbox.zsh [--peek]

Print unread control-plane notifications. By default, marks printed
notifications as read. Use --peek to leave the read offset unchanged.
USAGE
}

peek=0
while (( $# )); do
  case "$1" in
    --peek) peek=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; dispatch_fail "unknown argument: $1" ;;
  esac
done

root=$(dispatch_root)
control_dir="$root/control-plane"
inbox="$control_dir/inbox.ndjson"
offset_file="$control_dir/read.offset"
mkdir -p "$control_dir"
touch "$inbox"

offset=0
if [[ -f "$offset_file" ]]; then
  offset=$(cat "$offset_file")
fi
[[ "$offset" =~ '^[0-9]+$' ]] || offset=0

total=$(wc -l < "$inbox" | tr -d ' ')
if (( total <= offset )); then
  printf 'no unread dispatch notifications\n'
  exit 0
fi

start=$((offset + 1))
sed -n "${start},${total}p" "$inbox"

if (( peek == 0 )); then
  printf '%s\n' "$total" > "$offset_file"
fi
