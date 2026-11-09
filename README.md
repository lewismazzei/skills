# Agent Skills

The agent skills I use: my own, plus every third-party skill I have installed.

## How this repo works

- `skills.json` lists every installed skill with its source repository, pinned commit, agents, and why I keep it.
- `./install.sh` installs exactly that list. `./install.sh --dry-run` prints the commands instead.
- To update a skill, move its pin to a reviewed commit at least three days old, then run `./install.sh`.
- My own skills live in top-level directories, each with a section below.
- A third-party skill I have modified lives under a folder named for its source, with the source's licence and a `CHANGES.md`.

Skills that other tools install themselves, such as terminal-browser's, are not listed.

## pstack/architect

My copy of [pstack](https://github.com/cursor/plugins/tree/main/pstack)'s `architect` skill (Lauren Tan, MIT), without its optional step that points to `interrogate`, which I don't install. `pstack/architect/CHANGES.md` records the upstream commit and the change.
