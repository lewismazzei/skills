import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

import type {
  CliOptions,
  Confidence,
  CoverageGap,
  FixtureInput,
  NormalizedSchema,
  RedactionEvent,
  SchemaField,
} from "./types.js";

const DEFAULTS = {
  maxMinutes: 20,
  maxStates: 120,
  maxActions: 600,
  maxDepth: 2,
  maxPages: 120,
  maxActionsPerState: 12,
};

function parseBooleanFlag(args: string[], name: string): boolean {
  return args.includes(name);
}

function parseValueFlag(args: string[], name: string): string | undefined {
  const idx = args.indexOf(name);
  if (idx === -1) {
    return undefined;
  }
  return args[idx + 1];
}

function parseNumberFlag(args: string[], name: string, fallback: number): number {
  const raw = parseValueFlag(args, name);
  if (raw === undefined) {
    return fallback;
  }
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function parseCsv(raw?: string): string[] {
  if (!raw) {
    return [];
  }
  return raw
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export function hashOf(value: string): string {
  return crypto.createHash("sha1").update(value).digest("hex").slice(0, 16);
}

export function stableId(prefix: string, value: string): string {
  return `${prefix}-${hashOf(value)}`;
}

export function slugify(value: string): string {
  const normalized = value
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || "item";
}

export function timestampForFile(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return [
    date.getUTCFullYear(),
    pad(date.getUTCMonth() + 1),
    pad(date.getUTCDate()),
  ].join("") +
    "-" +
    [pad(date.getUTCHours()), pad(date.getUTCMinutes()), pad(date.getUTCSeconds())].join("");
}

export async function parseCliArgs(argv: string[]): Promise<CliOptions> {
  const valueFlags = new Set([
    "--out-dir",
    "--storage-state",
    "--allowed-origins",
    "--max-minutes",
    "--max-states",
    "--max-actions",
    "--max-depth",
    "--max-pages",
    "--max-actions-per-state",
    "--focus",
    "--fixtures",
    "--user-agent",
  ]);
  let url: string | undefined;
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token) {
      continue;
    }
    if (token.startsWith("--")) {
      if (valueFlags.has(token)) {
        i += 1;
      }
      continue;
    }
    url = token;
    break;
  }
  if (!url) {
    throw new Error("Missing required URL. Usage: analyze.ts <url> [flags]");
  }

  const outDir = parseValueFlag(argv, "--out-dir");
  const yes = parseBooleanFlag(argv, "--yes");
  const options: CliOptions = {
    url,
    yes,
    overwrite: parseBooleanFlag(argv, "--overwrite"),
    safeMode: parseBooleanFlag(argv, "--safe-mode"),
    dryRun: parseBooleanFlag(argv, "--dry-run"),
    mobile: parseBooleanFlag(argv, "--mobile"),
    fetchCrossOriginScripts: parseBooleanFlag(argv, "--fetch-cross-origin-scripts"),
    allowedOrigins: parseCsv(parseValueFlag(argv, "--allowed-origins")),
    maxMinutes: parseNumberFlag(argv, "--max-minutes", DEFAULTS.maxMinutes),
    maxStates: parseNumberFlag(argv, "--max-states", DEFAULTS.maxStates),
    maxActions: parseNumberFlag(argv, "--max-actions", DEFAULTS.maxActions),
    maxDepth: parseNumberFlag(argv, "--max-depth", DEFAULTS.maxDepth),
    maxPages: parseNumberFlag(argv, "--max-pages", DEFAULTS.maxPages),
    maxActionsPerState: parseNumberFlag(
      argv,
      "--max-actions-per-state",
      DEFAULTS.maxActionsPerState
    ),
    focus: parseCsv(parseValueFlag(argv, "--focus")),
    allowSensitiveOutput: parseBooleanFlag(argv, "--allow-sensitive-output"),
    mergedSpec: !parseBooleanFlag(argv, "--no-merged-spec"),
  };
  if (outDir) {
    options.outDir = outDir;
  }
  const storageState = parseValueFlag(argv, "--storage-state");
  if (storageState) {
    options.storageState = storageState;
  }
  const fixturesPath = parseValueFlag(argv, "--fixtures");
  if (fixturesPath) {
    options.fixturesPath = fixturesPath;
  }
  const userAgent = parseValueFlag(argv, "--user-agent");
  if (userAgent) {
    options.userAgent = userAgent;
  }
  return options;
}

export async function confirmDefaultOutDir(defaultOutDir: string): Promise<boolean> {
  if (!input.isTTY || !output.isTTY) {
    return true;
  }
  const rl = readline.createInterface({ input, output });
  try {
    const answer = await rl.question(`Use default output directory "${defaultOutDir}"? [Y/n] `);
    const normalized = answer.trim().toLowerCase();
    return normalized === "" || normalized === "y" || normalized === "yes";
  } finally {
    rl.close();
  }
}

export async function ensureRunDirectories(
  requestedOutDir: string,
  siteSlug: string,
  overwrite: boolean
): Promise<{ runDir: string; pagesDir: string; screenshotsDir: string; htmlDir: string }> {
  const timestamp = timestampForFile(new Date());
  const runDir = overwrite
    ? requestedOutDir
    : path.join(requestedOutDir, `${siteSlug}-${timestamp}`);

  if (overwrite) {
    await fs.rm(runDir, { recursive: true, force: true });
  }
  await fs.mkdir(runDir, { recursive: true });

  const pagesDir = path.join(runDir, "pages");
  const screenshotsDir = path.join(runDir, "screenshots");
  const htmlDir = path.join(runDir, "html");
  await fs.mkdir(pagesDir, { recursive: true });
  await fs.mkdir(screenshotsDir, { recursive: true });
  await fs.mkdir(htmlDir, { recursive: true });
  return { runDir, pagesDir, screenshotsDir, htmlDir };
}

export function clampText(text: string, maxLength = 800): string {
  const trimmed = text.replace(/\s+/g, " ").trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength)}...`;
}

function inferType(value: unknown): string {
  if (Array.isArray(value)) {
    return "array";
  }
  if (value === null) {
    return "null";
  }
  return typeof value;
}

function isLikelyRequired(values: unknown[]): boolean {
  return values.every((value) => value !== undefined && value !== null && value !== "");
}

export function normalizeEntitySchema(
  entityName: string,
  samples: Array<Record<string, unknown>>,
  sourceRefs: string[]
): NormalizedSchema {
  const fieldMap = new Map<string, unknown[]>();
  for (const sample of samples) {
    for (const [k, v] of Object.entries(sample)) {
      const values = fieldMap.get(k) ?? [];
      values.push(v);
      fieldMap.set(k, values);
    }
  }

  const fields: SchemaField[] = [];
  for (const [name, values] of [...fieldMap.entries()].sort(([a], [b]) =>
    a.localeCompare(b)
  )) {
    const first = values.find((v) => v !== undefined);
    fields.push({
      name,
      inferredType: inferType(first),
      required: isLikelyRequired(values),
      example: JSON.stringify(first ?? null),
    });
  }

  return {
    entity: entityName,
    fields,
    sampleCount: samples.length,
    sourceRefs: [...new Set(sourceRefs)],
  };
}

const REDACTION_PATTERNS: Array<{
  category: RedactionEvent["category"];
  regex: RegExp;
  replacement: string;
}> = [
  {
    category: "authorization",
    regex: /\b(Bearer\s+[A-Za-z0-9\-._~+/]+=*)\b/g,
    replacement: "Bearer [REDACTED_AUTH]",
  },
  {
    category: "api-key",
    regex: /\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{10,}\b/g,
    replacement: "[REDACTED_API_KEY]",
  },
  {
    category: "token",
    regex: /\b(?:xox[pbar]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,})\b/g,
    replacement: "[REDACTED_TOKEN]",
  },
  {
    category: "email",
    regex: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,
    replacement: "[REDACTED_EMAIL]",
  },
  {
    category: "phone",
    regex: /\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b/g,
    replacement: "[REDACTED_PHONE]",
  },
  {
    category: "ssn-like",
    regex: /\b\d{3}-\d{2}-\d{4}\b/g,
    replacement: "[REDACTED_SSN]",
  },
];

export function redactText(
  inputText: string,
  events: RedactionEvent[],
  enabled: boolean
): string {
  if (!enabled) {
    return inputText;
  }
  let text = inputText;
  for (const pattern of REDACTION_PATTERNS) {
    text = text.replace(pattern.regex, (match) => {
      events.push({
        category: pattern.category,
        sample: clampText(match, 64),
      });
      return pattern.replacement;
    });
  }
  return text;
}

export function redactUnknown<T>(inputValue: T, events: RedactionEvent[], enabled: boolean): T {
  if (!enabled) {
    return inputValue;
  }
  if (typeof inputValue === "string") {
    return redactText(inputValue, events, enabled) as T;
  }
  if (Array.isArray(inputValue)) {
    return inputValue.map((v) => redactUnknown(v, events, enabled)) as T;
  }
  if (inputValue && typeof inputValue === "object") {
    const next: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(inputValue as Record<string, unknown>)) {
      next[k] = redactUnknown(v, events, enabled);
    }
    return next as T;
  }
  return inputValue;
}

export function confidenceFromEvidence(params: {
  runtimeObserved: boolean;
  sourceRefs: number;
  inferredOnly?: boolean;
}): Confidence {
  if (params.inferredOnly) {
    return "low";
  }
  if (params.runtimeObserved && params.sourceRefs > 0) {
    return "high";
  }
  if (params.runtimeObserved || params.sourceRefs > 0) {
    return "medium";
  }
  return "low";
}

export async function readFixture(pathLike?: string): Promise<FixtureInput | undefined> {
  if (!pathLike) {
    return undefined;
  }
  const raw = await fs.readFile(pathLike, "utf8");
  const parsed = JSON.parse(raw) as FixtureInput;
  return parsed;
}

export async function writeTextFile(
  filePath: string,
  content: string,
  events: RedactionEvent[],
  redactionEnabled: boolean
): Promise<void> {
  const redacted = redactText(content, events, redactionEnabled);
  await fs.writeFile(filePath, redacted, "utf8");
}

export async function writeJsonFile<T>(
  filePath: string,
  value: T,
  events: RedactionEvent[],
  redactionEnabled: boolean
): Promise<void> {
  const redacted = redactUnknown(value, events, redactionEnabled);
  const content = JSON.stringify(redacted, null, 2);
  await fs.writeFile(filePath, `${content}\n`, "utf8");
}

export function deriveCoverageGap(
  category: CoverageGap["category"],
  detail: string
): CoverageGap {
  return {
    id: stableId("gap", `${category}:${detail}`),
    category,
    detail,
  };
}
