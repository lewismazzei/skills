#!/usr/bin/env bash
# Install every skill listed in skills.json at its pinned commit.
# Usage: ./install.sh [--dry-run]
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
dry=${1:-}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

cmds=$(python3 -I - "$here/skills.json" "$work" <<'PY'
import json, shlex, sys
from collections import defaultdict
manifest, work = sys.argv[1], sys.argv[2]
groups = defaultdict(list)
for s in json.load(open(manifest))["skills"]:
    parent = s["path"].rpartition("/")[0]
    groups[(s["source"], s["commit"], parent, tuple(s["agents"]))].append(s["name"])
for (source, commit, parent, agents), names in groups.items():
    checkout = f"{work}/{source.replace('/', '__')}-{commit[:12]}"
    fetch = (f"[ -d {shlex.quote(checkout)} ] || "
             f"{{ git clone -q --filter=blob:none --no-checkout https://github.com/{source}.git {shlex.quote(checkout)} "
             f"&& git -C {shlex.quote(checkout)} checkout -q {commit}; }}")
    add = ["skills", "add", f"{checkout}/{parent}".rstrip("/"), "-g", "-y"]
    for a in agents: add += ["-a", a]
    for n in names: add += ["-s", n]
    print(f"{fetch} && {shlex.join(add)}")
PY
)

failed=0
while IFS= read -r cmd; do
  echo "+ $cmd"
  [ "$dry" = "--dry-run" ] && continue
  (cd "$work" && eval "$cmd") >/dev/null 2>&1 </dev/null || { echo "  failed"; failed=$((failed + 1)); }
done <<< "$cmds"
[ "$failed" -eq 0 ] || { echo "$failed install command(s) failed"; exit 1; }
