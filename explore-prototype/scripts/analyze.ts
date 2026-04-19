import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { chromium, type BrowserContext, type Page } from "playwright";

import { extractFromSources } from "./source-extract.js";
import { renderSpecs } from "./spec.js";
import type {
  ActionTarget,
  AnalysisJson,
  CliOptions,
  CoverageGap,
  DiagnosticItem,
  DiscoveredAction,
  FixtureInput,
  NavigationEdge,
  RedactionEvent,
  RequirementItem,
  RunMetadata,
  StateSummary,
} from "./types.js";
import {
  clampText,
  confirmDefaultOutDir,
  deriveCoverageGap,
  ensureRunDirectories,
  hashOf,
  parseCliArgs,
  readFixture,
  slugify,
  stableId,
  writeJsonFile,
  writeTextFile,
} from "./utils.js";

const TOOL_VERSION = "0.1.0";
const SCHEMA_VERSION = "1.0.0";

interface CapturedStateInternal {
  summary: StateSummary;
  html: string;
}

interface QueueItem {
  path: ActionTarget[];
  depth: number;
}

function nowIso(): string {
  return new Date().toISOString();
}

function safeUrl(input: string): URL {
  try {
    return new URL(input);
  } catch {
    throw new Error(`Invalid URL: ${input}`);
  }
}

function defaultFixtureValue(inputType?: string): string {
  switch ((inputType || "").toLowerCase()) {
    case "email":
      return "prototype.user@example.com";
    case "number":
      return "42";
    case "tel":
      return "4155551234";
    case "url":
      return "https://example.com";
    case "date":
      return "2026-01-01";
    default:
      return "Prototype Sample";
  }
}

function isBranchAction(action: ActionTarget): boolean {
  return action.type === "click" || action.type === "submit";
}

function isExternal(targetUrl: string, baseOrigin: string, allowlist: string[]): boolean {
  try {
    const parsed = new URL(targetUrl, baseOrigin);
    if (parsed.origin === baseOrigin) {
      return false;
    }
    return !allowlist.includes(parsed.origin);
  } catch {
    return true;
  }
}

async function discoverActions(page: Page, baseOrigin: string): Promise<DiscoveredAction[]> {
  const raw = await page.evaluate(() => {
    const cssPath = (el: Element): string => {
      if (el.id) {
        return `#${CSS.escape(el.id)}`;
      }
      const testId = el.getAttribute("data-testid");
      if (testId) {
        return `[data-testid="${CSS.escape(testId)}"]`;
      }
      const parts: string[] = [];
      let current: Element | null = el;
      while (current && parts.length < 6) {
        const tag = current.tagName.toLowerCase();
        const className = (current.getAttribute("class") || "")
          .split(/\s+/)
          .filter(Boolean)
          .slice(0, 2)
          .map((c) => `.${CSS.escape(c)}`)
          .join("");
        const siblings = current.parentElement
          ? Array.from(current.parentElement.children).filter(
              (s) => s.tagName === current?.tagName
            )
          : [];
        const nth =
          siblings.length > 1
            ? `:nth-of-type(${siblings.indexOf(current) + 1})`
            : "";
        parts.unshift(`${tag}${className}${nth}`);
        current = current.parentElement;
      }
      return parts.join(" > ");
    };

    const nodes = Array.from(
      document.querySelectorAll(
      [
        "a[href]",
        "button",
        "input",
        "select",
        "textarea",
        "[role='button']",
        "[onclick]",
        "[data-page]",
        "[aria-controls]",
      ].join(",")
      )
    );

    const visible = (el: Element): boolean => {
      const style = window.getComputedStyle(el as HTMLElement);
      if (style.display === "none" || style.visibility === "hidden") {
        return false;
      }
      const rect = (el as HTMLElement).getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };

    const result = nodes
      .filter((el) => visible(el))
      .slice(0, 300)
      .map((el) => {
        const tag = el.tagName.toLowerCase();
        const text = (el.textContent || "").replace(/\s+/g, " ").trim();
        const aria = el.getAttribute("aria-label") || "";
        const label = text || aria || el.getAttribute("title") || tag;
        const role = el.getAttribute("role") || undefined;
        const href = el.getAttribute("href") || undefined;
        const onclick = el.getAttribute("onclick") || undefined;
        const dataPage = el.getAttribute("data-page") || undefined;
        const inputType = tag === "input" ? (el.getAttribute("type") || "text") : undefined;
        let type: "click" | "fill" | "select" | "toggle" | "submit" = "click";
        if (tag === "select") {
          type = "select";
        } else if (tag === "textarea") {
          type = "fill";
        } else if (tag === "input") {
          if (["checkbox", "radio"].includes((inputType || "").toLowerCase())) {
            type = "toggle";
          } else if ((inputType || "").toLowerCase() === "submit") {
            type = "submit";
          } else {
            type = "fill";
          }
        } else if (tag === "button" && ((el as HTMLButtonElement).type || "").toLowerCase() === "submit") {
          type = "submit";
        }

        return {
          selector: cssPath(el),
          label,
          tag,
          href,
          role,
          onclick,
          dataPage,
          inputType,
          type,
        };
      });
    return result;
  });

  const seen = new Map<string, DiscoveredAction>();
  for (const item of raw) {
    const signature = [
      item.type,
      item.tag,
      item.label,
      item.selector,
      item.href || "",
      item.onclick || "",
      item.dataPage || "",
    ].join("|");
    const id = stableId("action", signature);
    const confidence =
      item.href || item.dataPage || item.onclick || item.tag === "button" || item.role === "button"
        ? "high"
        : "medium";
    const hints: ActionTarget["hints"] = {
      tag: item.tag,
      ...(item.role ? { role: item.role } : {}),
      ...(item.onclick ? { onclick: item.onclick } : {}),
      ...(item.inputType ? { inputType: item.inputType } : {}),
      ...(item.href ? { href: String(new URL(item.href, baseOrigin)) } : {}),
    };
    const action: ActionTarget = {
      id,
      type: item.type,
      selector: item.selector,
      label: clampText(item.label || item.selector, 120),
      confidence,
      hints,
    };
    if (!seen.has(id)) {
      seen.set(id, { action, selector: item.selector });
    }
  }
  return [...seen.values()];
}

async function waitForSettled(page: Page): Promise<void> {
  try {
    await page.waitForLoadState("domcontentloaded", { timeout: 1000 });
  } catch {
    // no-op
  }
  await page.waitForTimeout(350);
}

async function executeAction(params: {
  page: Page;
  action: ActionTarget;
  options: CliOptions;
  baseOrigin: string;
  fixture: FixtureInput | undefined;
  diagnostics: DiagnosticItem[];
  coverageGaps: CoverageGap[];
}): Promise<boolean> {
  const { page, action, options, baseOrigin, fixture, diagnostics, coverageGaps } = params;
  const locator = page.locator(action.selector).first();
  if ((await locator.count()) === 0) {
    coverageGaps.push(
      deriveCoverageGap("blocked-action", `Selector not found for ${action.id}: ${action.selector}`)
    );
    return false;
  }

  if (action.hints.href && isExternal(action.hints.href, baseOrigin, options.allowedOrigins)) {
    coverageGaps.push(
      deriveCoverageGap("blocked-action", `Skipped external target for ${action.id}: ${action.hints.href}`)
    );
    return false;
  }

  if (options.safeMode && !["click", "submit"].includes(action.type)) {
    return false;
  }

  try {
    if (action.type === "click" || action.type === "submit") {
      await locator.click({ timeout: 5000, force: true });
    } else if (action.type === "fill") {
      const fixtureKey = action.label.toLowerCase();
      const explicit = fixture?.defaults?.[fixtureKey];
      const fallback = defaultFixtureValue(action.hints.inputType);
      await locator.fill(String(explicit ?? fallback), { timeout: 5000 });
    } else if (action.type === "select") {
      await locator.selectOption({ index: 1 }, { timeout: 5000 }).catch(async () => {
        await locator.selectOption({ index: 0 }, { timeout: 5000 });
      });
    } else if (action.type === "toggle") {
      const checked = await locator.isChecked().catch(() => false);
      if (checked) {
        await locator.uncheck({ timeout: 5000 }).catch(async () => {
          await locator.click({ timeout: 5000, force: true });
        });
      } else {
        await locator.check({ timeout: 5000 }).catch(async () => {
          await locator.click({ timeout: 5000, force: true });
        });
      }
    }
    await waitForSettled(page);
    return true;
  } catch (error) {
    diagnostics.push({
      type: "info",
      severity: "medium",
      message: `Action execution failed for ${action.id}: ${(error as Error).message}`,
      timestamp: nowIso(),
    });
    return false;
  }
}

async function materializePath(params: {
  page: Page;
  options: CliOptions;
  baseUrl: string;
  baseOrigin: string;
  pathActions: ActionTarget[];
  fixture: FixtureInput | undefined;
  diagnostics: DiagnosticItem[];
  coverageGaps: CoverageGap[];
}): Promise<boolean> {
  const { page, options, baseUrl, baseOrigin, pathActions, fixture, diagnostics, coverageGaps } = params;
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  await waitForSettled(page);

  for (const action of pathActions) {
    const ok = await executeAction({
      page,
      action,
      options,
      baseOrigin,
      fixture,
      diagnostics,
      coverageGaps,
    });
    if (!ok) {
      return false;
    }
  }
  return true;
}

async function captureState(params: {
  page: Page;
  depth: number;
  actionPath: string[];
  stateCounter: number;
  paths: { screenshotsDir: string; htmlDir: string };
  redactionEvents: RedactionEvent[];
  redactionEnabled: boolean;
}): Promise<CapturedStateInternal> {
  const { page, depth, actionPath, stateCounter, paths, redactionEvents, redactionEnabled } = params;
  const id = `state-${String(stateCounter).padStart(4, "0")}`;
  const title = await page.title();
  const url = page.url();

  const domSnapshot = await page.evaluate(() => {
    const text = (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 4000);
    const tags = [...document.querySelectorAll("*")]
      .slice(0, 400)
      .map((el) => `${el.tagName.toLowerCase()}:${el.getAttribute("role") || ""}`)
      .join("|");
    const hints: string[] = [];
    const detectors: Array<[string, string]> = [
      ["card", ".card, [class*='card']"],
      ["modal", "dialog, [role='dialog'], .modal"],
      ["table", "table, [role='table']"],
      ["form", "form, input, select, textarea"],
      ["chart", "svg, canvas, [class*='chart']"],
      ["tabs", "[role='tablist'], [role='tab']"],
      ["accordion", "[aria-expanded], [class*='accordion']"],
    ];
    for (const [name, selector] of detectors) {
      if (document.querySelector(selector)) {
        hints.push(name);
      }
    }
    return { text, tags, hints };
  });
  const fingerprint = hashOf(`${new URL(url).origin}${new URL(url).pathname}|${domSnapshot.tags}|${domSnapshot.text}`);

  const screenshotViewport = `screenshots/${id}.viewport.png`;
  const screenshotFull = `screenshots/${id}.full.png`;
  await page.screenshot({
    path: path.join(paths.screenshotsDir, `${id}.viewport.png`),
    fullPage: false,
  });
  await page.screenshot({
    path: path.join(paths.screenshotsDir, `${id}.full.png`),
    fullPage: true,
  });

  const modalScreenshots: string[] = [];
  const modalCount = await page
    .locator("dialog, [role='dialog'], .modal, [aria-modal='true']")
    .count();
  for (let i = 0; i < Math.min(3, modalCount); i += 1) {
    const modalPath = `screenshots/${id}.modal-${String(i + 1).padStart(2, "0")}.png`;
    await page
      .locator("dialog, [role='dialog'], .modal, [aria-modal='true']")
      .nth(i)
      .screenshot({ path: path.join(paths.screenshotsDir, `${id}.modal-${String(i + 1).padStart(2, "0")}.png`) })
      .then(() => {
        modalScreenshots.push(modalPath);
      })
      .catch(() => {
        // ignore modal screenshot failures
      });
  }

  const html = await page.content();
  const htmlPath = `html/${id}.html`;
  await writeTextFile(path.join(paths.htmlDir, `${id}.html`), html, redactionEvents, redactionEnabled);

  return {
    summary: {
      id,
      url,
      title: title || "Untitled",
      fingerprint,
      depth,
      actionPath,
      discoveredAt: nowIso(),
      screenshotViewport,
      screenshotFull,
      modalScreenshots,
      htmlSnapshot: htmlPath,
      componentHints: domSnapshot.hints,
      textSnippet: clampText(domSnapshot.text, 220),
    },
    html,
  };
}

function gatherInlineScripts(html: string): string[] {
  const out: string[] = [];
  const regex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(html))) {
    const body = (match[1] || "").trim();
    if (body.length > 20) {
      out.push(body);
    }
  }
  return out;
}

function gatherScriptSources(html: string, pageUrl: string): string[] {
  const out: string[] = [];
  const regex = /<script\b[^>]*src=["']([^"']+)["'][^>]*>/gi;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(html))) {
    const src = match[1];
    if (!src) {
      continue;
    }
    try {
      out.push(String(new URL(src, pageUrl)));
    } catch {
      // skip invalid URLs
    }
  }
  return out;
}

async function fetchSourceAsset(url: string): Promise<string | undefined> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);
    if (!response.ok) {
      return undefined;
    }
    const type = response.headers.get("content-type") || "";
    if (!/(javascript|text|json|html)/i.test(type)) {
      return undefined;
    }
    return await response.text();
  } catch {
    return undefined;
  }
}

function buildRequirements(states: StateSummary[], actions: ActionTarget[]): RequirementItem[] {
  const requirements: RequirementItem[] = [];
  const byPage = new Map<string, StateSummary[]>();
  for (const state of states) {
    const key = `${state.title}|${new URL(state.url).pathname}`;
    const list = byPage.get(key) ?? [];
    list.push(state);
    byPage.set(key, list);
  }

  for (const [key, group] of byPage.entries()) {
    const [titleRaw, pathNameRaw] = key.split("|");
    const title = titleRaw ?? "Untitled";
    const pathName = pathNameRaw ?? "/";
    const pathNeedle = pathName.toLowerCase().replace(/\//g, " ").trim();
    const sourceStateIds = group.map((s) => s.id);
    const relatedActions = actions
      .filter((a) => {
        const label = a.label.toLowerCase();
        return (
          label.includes(title.toLowerCase()) ||
          (pathNeedle.length > 0 && label.includes(pathNeedle))
        );
      })
      .slice(0, 10);
    const criteria = [
      `Render ${title} view at ${pathName}.`,
      "Support the interactions captured in prototype exploration.",
      "Match visible component and layout patterns from screenshots.",
    ];
    if (relatedActions.length > 0) {
      criteria.push(
        `Implement key actions: ${relatedActions.map((a) => `"${a.label}"`).join(", ")}.`
      );
    }
    requirements.push({
      id: stableId("req", `${title}|${pathName}|${sourceStateIds.join(",")}`),
      title: `Implement ${title || "Untitled"} page`,
      acceptanceCriteria: criteria,
      dataDependencies: group.flatMap((state) => state.componentHints).slice(0, 8),
      sourceStateIds,
    });
  }

  return requirements.slice(0, 200);
}

function formatSummary(analysis: AnalysisJson, runDir: string): string {
  const covered = [
    `states=${analysis.states.length}`,
    `actions=${analysis.actions.length}`,
    `edges=${analysis.navigation_edges.length}`,
    `snippets=${analysis.extracted_snippets.length}`,
  ].join(", ");
  const skipped = analysis.coverage_gaps.length;
  const suggestions: string[] = [];
  if (analysis.coverage_gaps.some((gap) => gap.category === "auth")) {
    suggestions.push("--storage-state <path>");
  }
  if (analysis.coverage_gaps.some((gap) => gap.category === "budget")) {
    suggestions.push("--max-minutes 30 --max-states 200 --max-actions 1000");
  }
  if (analysis.coverage_gaps.some((gap) => gap.category === "script-skip")) {
    suggestions.push("--fetch-cross-origin-scripts");
  }
  if (suggestions.length === 0) {
    suggestions.push("--focus \"roi,ai responses,onboarding\"");
  }

  return [
    "POST-RUN SUMMARY",
    `Covered: ${covered}`,
    `Skipped: ${skipped} coverage gap(s)`,
    `Artifacts: ${runDir}`,
    `Recommended next-run flags: ${suggestions.join(" | ")}`,
  ].join("\n");
}

async function run(): Promise<void> {
  const options = await parseCliArgs(process.argv.slice(2));
  const parsedUrl = safeUrl(options.url);
  const baseOrigin = parsedUrl.origin;
  const cwd = process.cwd();
  const defaultOutDir = path.join(cwd, "prototype-specs");
  const requestedOutDir = options.outDir ?? defaultOutDir;

  if (!options.outDir && !options.yes) {
    const confirmed = await confirmDefaultOutDir(defaultOutDir);
    if (!confirmed) {
      throw new Error("Output directory not confirmed.");
    }
  }

  const siteSlug = slugify(`${parsedUrl.hostname}${parsedUrl.pathname}`);
  const runPaths = await ensureRunDirectories(requestedOutDir, siteSlug, options.overwrite);
  const redactionEvents: RedactionEvent[] = [];
  const redactionEnabled = !options.allowSensitiveOutput;
  const coverageGaps: CoverageGap[] = [];

  const runStarted = Date.now();
  const metadata: RunMetadata = {
    schemaVersion: SCHEMA_VERSION,
    toolVersion: TOOL_VERSION,
    startedAt: nowIso(),
    cwd,
    url: parsedUrl.toString(),
    urlHash: hashOf(parsedUrl.toString()),
    outDir: requestedOutDir,
    runDir: runPaths.runDir,
    flags: {
      dryRun: options.dryRun,
      safeMode: options.safeMode,
      mobile: options.mobile,
      overwrite: options.overwrite,
      fetchCrossOriginScripts: options.fetchCrossOriginScripts,
      allowedOrigins: options.allowedOrigins,
      maxMinutes: options.maxMinutes,
      maxStates: options.maxStates,
      maxActions: options.maxActions,
      maxDepth: options.maxDepth,
      maxPages: options.maxPages,
      maxActionsPerState: options.maxActionsPerState,
      focus: options.focus,
      mergedSpec: options.mergedSpec,
    },
    viewport: {
      width: options.mobile ? 390 : 1440,
      height: options.mobile ? 844 : 900,
      mobile: options.mobile,
    },
    userAgent: options.userAgent || "default-playwright",
    nodeVersion: process.version,
    platform: process.platform,
  };

  const fixture = await readFixture(options.fixturesPath);
  const diagnostics: DiagnosticItem[] = [];
  const stateByFingerprint = new Map<string, StateSummary>();
  const capturedStates = new Map<string, CapturedStateInternal>();
  const actionById = new Map<string, ActionTarget>();
  const edges: NavigationEdge[] = [];
  const uniquePageUrls = new Set<string>();

  const browser = await chromium.launch({ headless: true });
  const contextOptions: Parameters<typeof browser.newContext>[0] = {
    viewport: metadata.viewport,
  };
  if (options.userAgent) {
    contextOptions.userAgent = options.userAgent;
  }
  if (options.storageState) {
    contextOptions.storageState = options.storageState;
  }
  const context: BrowserContext = await browser.newContext(contextOptions);
  const page: Page = await context.newPage();

  page.on("console", (msg) => {
    if (msg.type() === "error" || msg.type() === "warning") {
      diagnostics.push({
        type: msg.type() === "error" ? "console-error" : "console-warning",
        severity: msg.type() === "error" ? "high" : "medium",
        message: msg.text(),
        timestamp: nowIso(),
        url: page.url(),
      });
    }
  });
  page.on("requestfailed", (request) => {
    diagnostics.push({
      type: "request-failed",
      severity: "medium",
      message: `Request failed: ${request.method()} ${request.url()} (${request.failure()?.errorText ?? "unknown"})`,
      timestamp: nowIso(),
      url: request.url(),
    });
  });

  const queue: QueueItem[] = [{ path: [], depth: 0 }];
  const visitedPathKeys = new Set<string>();
  let actionCount = 0;
  let stateCounter = 0;

  const deadline = runStarted + options.maxMinutes * 60 * 1000;

  while (queue.length > 0) {
    if (Date.now() > deadline) {
      coverageGaps.push(
        deriveCoverageGap("budget", `Exceeded max runtime of ${options.maxMinutes} minutes`)
      );
      break;
    }
    if (stateByFingerprint.size >= options.maxStates) {
      coverageGaps.push(deriveCoverageGap("budget", `Reached max_states=${options.maxStates}`));
      break;
    }
    if (actionCount >= options.maxActions) {
      coverageGaps.push(deriveCoverageGap("budget", `Reached max_actions=${options.maxActions}`));
      break;
    }

    const item = queue.shift();
    if (!item) {
      break;
    }
    const pathKey = item.path.map((a) => a.id).join(">");
    if (visitedPathKeys.has(pathKey)) {
      continue;
    }
    visitedPathKeys.add(pathKey);

    const materialized = await materializePath({
      page,
      options,
      baseUrl: parsedUrl.toString(),
      baseOrigin,
      pathActions: item.path,
      fixture,
      diagnostics,
      coverageGaps,
    });
    if (!materialized) {
      coverageGaps.push(
        deriveCoverageGap("blocked-action", `Failed to materialize action path: ${pathKey || "<root>"}`)
      );
      continue;
    }

    const currentUrl = page.url();
    if (new URL(currentUrl).origin !== baseOrigin && !options.allowedOrigins.includes(new URL(currentUrl).origin)) {
      coverageGaps.push(
        deriveCoverageGap("blocked-action", `Path escaped allowed origins: ${currentUrl}`)
      );
      continue;
    }

    const currentPath = new URL(currentUrl).pathname;
    uniquePageUrls.add(currentPath);
    if (uniquePageUrls.size > options.maxPages) {
      coverageGaps.push(deriveCoverageGap("budget", `Reached max_pages=${options.maxPages}`));
      break;
    }

    stateCounter += 1;
    const captured = await captureState({
      page,
      depth: item.depth,
      actionPath: item.path.map((a) => a.id),
      stateCounter,
      paths: runPaths,
      redactionEvents,
      redactionEnabled,
    });

    let currentState = stateByFingerprint.get(captured.summary.fingerprint);
    if (!currentState) {
      currentState = captured.summary;
      stateByFingerprint.set(captured.summary.fingerprint, captured.summary);
      capturedStates.set(captured.summary.id, captured);
    } else {
      stateCounter -= 1;
    }

    const discovered = await discoverActions(page, baseOrigin);
    for (const d of discovered) {
      actionById.set(d.action.id, d.action);
    }

    if (options.dryRun) {
      continue;
    }

    const actionable = discovered.slice(0, options.maxActionsPerState);
    for (const d of actionable) {
      if (actionCount >= options.maxActions) {
        break;
      }
      actionCount += 1;

      const baseReady = await materializePath({
        page,
        options,
        baseUrl: parsedUrl.toString(),
        baseOrigin,
        pathActions: item.path,
        fixture,
        diagnostics,
        coverageGaps,
      });
      if (!baseReady) {
        break;
      }

      const ok = await executeAction({
        page,
        action: d.action,
        options,
        baseOrigin,
        fixture,
        diagnostics,
        coverageGaps,
      });
      if (!ok) {
        continue;
      }

      const urlAfter = page.url();
      if (new URL(urlAfter).origin !== baseOrigin && !options.allowedOrigins.includes(new URL(urlAfter).origin)) {
        coverageGaps.push(
          deriveCoverageGap("blocked-action", `Action escaped allowed origins: ${d.action.id}`)
        );
        continue;
      }

      stateCounter += 1;
      const nextCaptured = await captureState({
        page,
        depth: item.depth + 1,
        actionPath: [...item.path.map((a) => a.id), d.action.id],
        stateCounter,
        paths: runPaths,
        redactionEvents,
        redactionEnabled,
      });
      let nextState = stateByFingerprint.get(nextCaptured.summary.fingerprint);
      let discoveredNew = false;
      if (!nextState) {
        nextState = nextCaptured.summary;
        stateByFingerprint.set(nextCaptured.summary.fingerprint, nextCaptured.summary);
        capturedStates.set(nextCaptured.summary.id, nextCaptured);
        discoveredNew = true;
      } else {
        stateCounter -= 1;
      }

      if (currentState && nextState) {
        edges.push({
          fromStateId: currentState.id,
          toStateId: nextState.id,
          actionId: d.action.id,
          actionLabel: d.action.label,
        });
      }

      if (discoveredNew && item.depth + 1 <= options.maxDepth && isBranchAction(d.action)) {
        queue.push({
          path: [...item.path, d.action],
          depth: item.depth + 1,
        });
      }
    }
  }

  await context.close();
  await browser.close();

  const stateList = [...stateByFingerprint.values()].sort((a, b) => a.id.localeCompare(b.id));
  const actionList = [...actionById.values()].sort((a, b) => a.id.localeCompare(b.id));

  const sources: Array<{ id: string; ref: string; content: string }> = [];
  for (const state of stateList) {
    const captured = capturedStates.get(state.id);
    if (!captured) {
      continue;
    }
    sources.push({
      id: `${state.id}-html`,
      ref: `${state.htmlSnapshot}`,
      content: captured.html,
    });
    const inlineScripts = gatherInlineScripts(captured.html);
    for (let i = 0; i < inlineScripts.length; i += 1) {
      const inline = inlineScripts[i];
      if (!inline) {
        continue;
      }
      sources.push({
        id: `${state.id}-inline-${i + 1}`,
        ref: `${state.htmlSnapshot}#inline-${i + 1}`,
        content: inline,
      });
    }
  }

  const scriptUrls = new Set<string>();
  for (const state of stateList) {
    const captured = capturedStates.get(state.id);
    if (!captured) {
      continue;
    }
    const urls = gatherScriptSources(captured.html, state.url);
    for (const url of urls) {
      scriptUrls.add(url);
    }
  }

  for (const scriptUrl of scriptUrls) {
    const parsed = new URL(scriptUrl);
    if (parsed.origin !== baseOrigin && !options.fetchCrossOriginScripts) {
      coverageGaps.push(deriveCoverageGap("script-skip", `Skipped cross-origin script: ${scriptUrl}`));
      continue;
    }
    if (parsed.origin !== baseOrigin && !options.allowedOrigins.includes(parsed.origin)) {
      coverageGaps.push(
        deriveCoverageGap("script-skip", `Script outside allowed origins: ${scriptUrl}`)
      );
      continue;
    }
    const content = await fetchSourceAsset(scriptUrl);
    if (!content) {
      diagnostics.push({
        type: "info",
        severity: "low",
        message: `Unable to fetch script source: ${scriptUrl}`,
        timestamp: nowIso(),
        url: scriptUrl,
      });
      continue;
    }
    sources.push({
      id: `script-${hashOf(scriptUrl)}`,
      ref: scriptUrl,
      content,
    });
  }

  let extraction = {
    snippets: [] as AnalysisJson["extracted_snippets"],
    schemas: [] as AnalysisJson["normalized_schemas"],
    formulas: [] as AnalysisJson["formulas"],
    aiMaps: [] as AnalysisJson["ai_response_maps"],
  };
  if (!options.dryRun) {
    extraction = extractFromSources(sources);
  } else {
    coverageGaps.push(deriveCoverageGap("parsing", "Dry-run mode skips deep source parsing."));
  }

  const requirements = buildRequirements(stateList, actionList);

  metadata.finishedAt = nowIso();
  metadata.durationMs = Date.now() - runStarted;

  const analysis: AnalysisJson = {
    schema_version: SCHEMA_VERSION,
    metadata,
    states: stateList,
    actions: actionList,
    navigation_edges: edges,
    diagnostics,
    extracted_snippets: extraction.snippets,
    normalized_schemas: extraction.schemas,
    formulas: extraction.formulas,
    ai_response_maps: extraction.aiMaps,
    requirements_backlog: requirements,
    coverage_gaps: coverageGaps,
    redaction_report: {
      enabled: redactionEnabled,
      events: redactionEvents,
    },
  };

  const rendered = renderSpecs(analysis, runPaths.runDir);

  for (const pageFile of rendered.pages) {
    await writeTextFile(
      path.join(runPaths.pagesDir, pageFile.fileName),
      pageFile.content,
      redactionEvents,
      redactionEnabled
    );
  }

  await writeTextFile(path.join(runPaths.runDir, "index.md"), rendered.indexMd, redactionEvents, redactionEnabled);
  if (options.mergedSpec) {
    await writeTextFile(
      path.join(runPaths.runDir, "spec.md"),
      rendered.mergedSpecMd,
      redactionEvents,
      redactionEnabled
    );
  }
  await writeJsonFile(path.join(runPaths.runDir, "analysis.json"), analysis, redactionEvents, redactionEnabled);
  await writeJsonFile(path.join(runPaths.runDir, "run-manifest.json"), metadata, redactionEvents, redactionEnabled);

  console.log(formatSummary(analysis, runPaths.runDir));
}

run().catch(async (error) => {
  console.error(`explore-prototype-analyzer failed: ${(error as Error).message}`);
  await fs.writeFile(
    path.join(process.cwd(), "prototype-analysis-error.log"),
    `${nowIso()} ${(error as Error).stack ?? String(error)}\n`,
    "utf8"
  );
  process.exitCode = 1;
});
