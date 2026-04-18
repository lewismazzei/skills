---
name: to-linear-issues
description: Convert markdown task lists or planning notes into deduplicated Linear issues. Use when the user wants Matt Pocock-style "to-issues" capture flow but targeting Linear instead of GitHub.
---

# To Linear Issues

Use this skill to convert local planning text into actionable Linear issues with stable dedupe keys and predictable field mapping.

## When To Use

Use this skill when the user asks to:

- turn TODO bullets into Linear issues
- sync planning docs into Linear
- replace a GitHub issue capture flow with Linear
- run a dry run preview before creating issues

## Inputs

Collect these inputs from the user request or infer reasonable defaults:

- source file path(s) to parse
- Linear team key (required to create issues)
- optional project name
- optional default labels
- mode: `dry-run` or `create`

If team/project is missing, default to `dry-run` and ask one concise follow-up question only if creation is blocked.

## Workflow

1. Parse tasks from source files:
   - Unchecked checklist lines (`- [ ] ...`) are canonical tasks.
   - Use heading hierarchy as issue context.
   - Extract inline metadata:
     - `#label` -> label
     - `@user` -> assignee hint
     - `[P0]...[P4]` -> priority hint
2. Generate a stable external key per task to support idempotent upserts.
3. Resolve Linear entities:
   - team (required)
   - project/labels/assignee (optional)
4. Deduplicate before create:
   - prefer matching by external key in issue body
   - fallback match by normalized title in same team and active states
5. Show a dry-run preview table first unless user explicitly asks to create immediately.
6. Create issues in Linear and include source provenance in the body.
7. Report created/skipped/failed counts and list issue links.

## Parser Script

Use the bundled parser:

- `scripts/extract_tasks.py`

It outputs JSON task objects with:

- `title`
- `source_file`
- `source_line`
- `heading_path`
- `labels`
- `assignee`
- `priority`
- `external_key`
- `body_markdown`

Run it for preview parsing before any Linear mutation.

## Linear Field Mapping

Use this default mapping unless the user overrides:

- title: parser `title`
- description: parser `body_markdown`
- team: user-specified team key
- project: optional by exact name
- labels: parser labels + user defaults
- assignee: parser assignee hint (best effort)
- priority:
  - `P0` -> urgent
  - `P1` -> high
  - `P2` -> medium
  - `P3/P4` -> low

When mapping is ambiguous, keep defaults and mention assumptions.

## Dedupe Contract

Every created issue description should include:

`External-Key: <external_key>`

Before creating an issue, search existing active issues in the target team for the same external key. If found, skip creation and report as existing.

## Output Contract

Always return:

- mode used (`dry-run` or `create`)
- source files parsed
- target team/project
- counts (parsed, creatable, created, skipped, failed)
- list of issue titles with links or reason skipped

## Safety

- Default to `dry-run` when creation intent is unclear.
- Do not create issues without a target team.
- Never discard source context; include provenance in issue description.
