# explore-prototype

Hybrid skill package for turning prototype URLs into implementation-ready specs.

## Quick Start

Install dependencies:

```bash
npm install
```

Run analyzer:

```bash
npm run analyze -- "https://example.netlify.app"
```

Outputs are written to:

- default: `<current-working-directory>/prototype-specs`
- override: `--out-dir <path>`

## Development

Typecheck:

```bash
npm run typecheck
```

Unit tests:

```bash
npm run test
```
