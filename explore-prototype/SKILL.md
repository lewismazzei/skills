---
name: explore-prototype
description: Build implementation-ready specs from interactive prototypes by combining Playwright exploration with source-level extraction. Use when the user provides a prototype URL and wants a structured spec, data models, formulas, hidden behaviors, and screenshot artifacts.
---

# Explore Prototype

Use this skill to analyze a prototype URL and emit a deterministic spec bundle:

- `index.md`
- `spec.md` (merged view)
- `pages/*.md`
- `analysis.json`
- `screenshots/*`
- `html/*`

## Authorization Requirement

Only analyze systems the user owns or is explicitly authorized to test.

## Known Limitations

- Canvas/WebGL-first UIs can hide text/structure from DOM extraction.
- Obfuscated/minified bundles reduce extraction quality.
- Anti-bot controls may limit interaction coverage.
- Auth-heavy prototypes require user-provided storage state.
- Screenshot pixels are not redacted in V1 (text outputs are redacted).

## Preflight Checklist

Before execution, confirm:

1. URL is reachable and authorized.
2. Output directory:
   - If user did not specify one, ask: "Use `<cwd>/prototype-specs`?"
3. Auth state:
   - If needed, gather `--storage-state`.
4. Runtime budget:
   - defaults: 20 minutes, 120 states, 600 actions.
5. Optional focus hints:
   - example: `roi, ai responses, onboarding`.

## Primary Workflow

1. Bootstrap runtime dependencies if missing.
2. Run analyzer on the provided URL.
3. Return standardized post-run summary.

Run bundled analyzer commands from this skill directory, not from the user's project directory. If the skill is installed globally, the active path is usually:

```bash
cd /home/codex/.codex/skills/explore-prototype
```

Default command pattern:

```bash
npm run analyze -- "<url>"
```

Use explicit output directory when user provides one:

```bash
npm run analyze -- "<url>" --out-dir "<path>"
```

Dry-run discovery mode:

```bash
npm run analyze -- "<url>" --dry-run
```

## Advanced Flags

- `--out-dir <path>`
- `--yes` (skip prompt)
- `--overwrite`
- `--safe-mode` (click-only interaction)
- `--dry-run`
- `--mobile`
- `--storage-state <path>`
- `--fetch-cross-origin-scripts`
- `--allowed-origins a.com,b.com`
- `--max-minutes <n>`
- `--max-states <n>`
- `--max-actions <n>`
- `--max-depth <n>`
- `--max-pages <n>`
- `--max-actions-per-state <n>`
- `--focus "x,y,z"`
- `--fixtures <path>`
- `--allow-sensitive-output`
- `--no-merged-spec`

## Output Contract (fixed order)

The merged spec must keep this top-level order:

1. Executive Summary
2. Run Metadata
3. Navigation Map
4. Design System
5. Data Models
6. Behavior & Logic
7. Page Specs
8. Requirements Backlog
9. Diagnostics
10. Coverage Gaps
11. Appendix (Artifacts)

Each page spec must use this sub-template:

1. Overview
2. Layout
3. Components
4. Interactions
5. Data Dependencies
6. AI Touchpoints
7. Open Questions

## Confidence Rubric

Use deterministic confidence labels:

- High: observed in runtime plus source evidence.
- Medium: source evidence only or runtime-only with limited corroboration.
- Low: inferred patterns without direct evidence snippet.

## Post-run Response Contract

Always report:

- What was covered.
- What was skipped.
- Where artifacts were written.
- Recommended next-run flags.
