#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:a:h}
. "$script_dir/dispatch-common.zsh"
setopt null_glob

root=$(dispatch_root)
workers_dir="$root/workers"

if [[ ! -d "$workers_dir" ]]; then
  printf 'no active dispatch workers\n'
  exit 0
fi

printf '%-20s %-12s %-8s %-8s %s\n' worker status dirty cleanup task
found=0
for worker_dir in "$workers_dir"/*; do
  [[ -d "$worker_dir" ]] || continue
  found=1
  name=$(dispatch_read "$worker_dir" name)
  worker_status=$(dispatch_read "$worker_dir" status)
  dirty=$(dispatch_read "$worker_dir" dirty)
  cleanup=$(dispatch_read "$worker_dir" cleanup_ready)
  task=$(dispatch_read "$worker_dir" task)
  printf '%-20s %-12s %-8s %-8s %s\n' "${name:-unknown}" "${worker_status:-unknown}" "${dirty:-unknown}" "${cleanup:-unknown}" "${task:-}"
done

if (( found == 0 )); then
  printf 'no active dispatch workers\n'
fi
