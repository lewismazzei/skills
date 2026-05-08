---
name: manage-personal-skills
description: Audit, install, rename, remove, or sync personal Codex skills while preserving the boundary between the personal source repo, third-party installs, and Codex runtime symlinks. Use whenever the user asks to manage skills, clean up skill directories, install third-party skills, update personal skills, or investigate drift between ~/skills, ~/.agents/skills, and ~/.codex/skills.
---

# Manage Personal Skills

Use this workflow for all skill install, cleanup, rename, removal, and sync work on this machine.

## Ownership Model

- `~/skills` is the source of truth for personal skills only.
- `~/.agents/skills` is the active global install directory for personal and third-party skills.
- `~/.codex/skills` should contain `.system` plus symlinks to `~/.agents/skills`.
- Third-party skills stay out of `~/skills` unless the user explicitly decides to fork one.
- Do not hand-edit personal skill files directly in `.agents` or `.codex`; edit the source repo first, then sync/install.

## Required Workflow

1. Run the audit before changes:

```bash
~/skills/manage-personal-skills/scripts/audit-skills.sh
```

2. Classify each skill before acting:
   - Personal source skill: belongs in `~/skills`, README, `.agents`, and `.codex` symlink.
   - Third-party skill: belongs in `.agents` and `.codex` symlink only.
   - System skill: stays in `.codex/skills/.system`.

3. For personal skill changes:
   - Update `~/skills/<skill-name>`.
   - Keep `SKILL.md` frontmatter `name` equal to the directory name.
   - Update `~/skills/README.md` in the same change.
   - Sync the active install from the source repo.
   - Ensure `.codex/skills/<skill-name>` is a symlink to `../../.agents/skills/<skill-name>`.

4. For third-party installs:
   - Use `npx skills add ... -g -a codex -y`.
   - If the installer only writes `.agents`, create the matching `.codex` symlink.
   - Do not add third-party files to `~/skills`.

5. Run the audit after changes and resolve any `ERROR` lines before committing.

## Bundled Script

Use `scripts/audit-skills.sh` for deterministic drift checks. It reports:

- Personal source skills missing README sections.
- `SKILL.md` names that do not match folder names.
- Personal source skills missing active installs.
- Personal source installs that differ from source, ignoring known generated files.
- Missing or non-symlink Codex runtime entries.
- Direct non-system skill directories under `.codex/skills`.

## Commit Discipline

When committing skill-management work, keep commits grouped by intent:

- Remove obsolete skills.
- Add or rename personal skills.
- Sync executable code changes.
- Normalize installed third-party skill layout.

Use the `git-commit` workflow for grouping and safety, and `caveman-commit` for the final commit message style.
