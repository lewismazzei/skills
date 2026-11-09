#!/usr/bin/env bash
# Install every skill listed in skills.json at its pinned commit.
# Usage: ./install.sh [--dry-run]
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
dry=${1:-}

cmds=$(python3 -I - "$here/skills.json" <<'PY'
import json, shlex, sys
from collections import defaultdict
groups = defaultdict(list)
for s in json.load(open(sys.argv[1]))["skills"]:
    parent = s["path"].rpartition("/")[0]
    groups[(s["source"], s["commit"], parent, tuple(s["agents"]))].append(s["name"])
for (source, commit, parent, agents), names in groups.items():
    url = f"https://github.com/{source}/tree/{commit}" + (f"/{parent}" if parent else "")
    args = ["skills", "add", url, "-g", "-y"]
    for a in agents: args += ["-a", a]
    for n in names: args += ["-s", n]
    print(shlex.join(args))
PY
)

failed=0
while IFS= read -r cmd; do
  echo "+ $cmd"
  [ "$dry" = "--dry-run" ] && continue
  (cd /tmp && eval "$cmd") >/dev/null 2>&1 </dev/null || { echo "  failed"; failed=$((failed + 1)); }
done <<< "$cmds"
[ "$failed" -eq 0 ] || { echo "$failed install command(s) failed"; exit 1; }
