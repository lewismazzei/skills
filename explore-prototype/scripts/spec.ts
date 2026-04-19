import type {
  AIResponseMap,
  AnalysisJson,
  CoverageGap,
  DiagnosticItem,
  FormulaSpec,
  NormalizedSchema,
  RequirementItem,
  StateSummary,
} from "./types.js";
import { clampText, slugify } from "./utils.js";

function sortByLabel<T>(items: T[], label: (item: T) => string): T[] {
  return [...items].sort((a, b) => label(a).localeCompare(label(b)));
}

function fmtDateIso(value: string): string {
  return new Date(value).toISOString();
}

function sectionHeader(level: number, title: string): string {
  return `${"#".repeat(level)} ${title}`;
}

function renderNavigationMap(states: StateSummary[], edges: AnalysisJson["navigation_edges"]): string {
  const byState = new Map(states.map((s) => [s.id, s]));
  const lines = [sectionHeader(2, "Navigation Map"), ""];
  if (states.length === 0) {
    lines.push("No navigable states were captured.");
    lines.push("");
    return lines.join("\n");
  }

  lines.push("| From | Action | To |");
  lines.push("| --- | --- | --- |");
  for (const edge of edges) {
    const from = byState.get(edge.fromStateId);
    const to = byState.get(edge.toStateId);
    lines.push(
      `| ${from?.id ?? edge.fromStateId} | ${edge.actionLabel.replace(/\|/g, "\\|")} | ${to?.id ?? edge.toStateId} |`
    );
  }
  lines.push("");
  return lines.join("\n");
}

function renderDesignSystem(snippets: AnalysisJson["extracted_snippets"]): string {
  const tokens = snippets.filter((s) => s.category === "design-token").slice(0, 120);
  const lines = [sectionHeader(2, "Design System"), ""];
  if (tokens.length === 0) {
    lines.push("No design tokens found.");
    lines.push("");
    return lines.join("\n");
  }
  lines.push("| Token | Value | Source |");
  lines.push("| --- | --- | --- |");
  for (const token of tokens) {
    lines.push(
      `| ${token.title} | ${token.content.replace(/\|/g, "\\|")} | ${token.sourceRef.replace(/\|/g, "\\|")} |`
    );
  }
  lines.push("");
  return lines.join("\n");
}

function renderSchemas(schemas: NormalizedSchema[]): string {
  const lines = [sectionHeader(2, "Data Models"), ""];
  if (schemas.length === 0) {
    lines.push("No normalized schemas were extracted.");
    lines.push("");
    return lines.join("\n");
  }
  for (const schema of sortByLabel(schemas, (s) => s.entity)) {
    lines.push(sectionHeader(3, schema.entity));
    lines.push("");
    lines.push(`Samples: ${schema.sampleCount}`);
    lines.push("");
    lines.push("| Field | Type | Required | Example |");
    lines.push("| --- | --- | --- | --- |");
    for (const field of schema.fields) {
      lines.push(
        `| ${field.name} | ${field.inferredType} | ${field.required ? "yes" : "no"} | ${field.example
          .replace(/\|/g, "\\|")
          .slice(0, 80)} |`
      );
    }
    lines.push("");
    lines.push(`Source refs: ${schema.sourceRefs.join(", ")}`);
    lines.push("");
  }
  return lines.join("\n");
}

function renderFormulas(formulas: FormulaSpec[], aiMaps: AIResponseMap[], snippets: AnalysisJson["extracted_snippets"]): string {
  const lines = [sectionHeader(2, "Behavior & Logic"), ""];
  lines.push(sectionHeader(3, "Formulae"));
  lines.push("");
  if (formulas.length === 0) {
    lines.push("No formula candidates extracted.");
    lines.push("");
  } else {
    for (const formula of formulas.slice(0, 60)) {
      lines.push(`- ${formula.name}: \`${formula.expression}\` (${formula.confidence})`);
      lines.push(`  - Evidence: ${formula.evidence}`);
      const sample = formula.examples[0];
      if (sample) {
        lines.push(
          `  - Sample: inputs ${JSON.stringify(sample.sampleInputs)} -> ${sample.expectedOutput}`
        );
      }
    }
    lines.push("");
  }

  lines.push(sectionHeader(3, "AI Response Maps"));
  lines.push("");
  if (aiMaps.length === 0) {
    lines.push("No AI response maps extracted.");
    lines.push("");
  } else {
    lines.push("| Trigger | Response Summary | Source | Confidence |");
    lines.push("| --- | --- | --- | --- |");
    for (const item of aiMaps.slice(0, 80)) {
      lines.push(
        `| ${item.trigger.replace(/\|/g, "\\|")} | ${clampText(item.response, 140).replace(/\|/g, "\\|")} | ${
          item.sourceRef
        } | ${item.confidence} |`
      );
    }
    lines.push("");
  }

  lines.push(sectionHeader(3, "Other Behavioral Signals"));
  lines.push("");
  const behavior = snippets.filter((s) =>
    ["gamification", "navigation-hook"].includes(s.category)
  );
  if (behavior.length === 0) {
    lines.push("No additional behavioral signals extracted.");
    lines.push("");
  } else {
    for (const item of behavior.slice(0, 80)) {
      lines.push(`- ${item.category}: ${clampText(item.content, 180)} (${item.sourceRef})`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

function groupStatesIntoPages(states: StateSummary[]): Map<string, StateSummary[]> {
  const grouped = new Map<string, StateSummary[]>();
  for (const state of states) {
    const key = `${state.title || "untitled"}|${state.url}`;
    const existing = grouped.get(key) ?? [];
    existing.push(state);
    grouped.set(key, existing);
  }
  return grouped;
}

function renderPageFileContent(pageKey: string, pageStates: StateSummary[], analysis: AnalysisJson): string {
  const [titleRaw, urlRaw] = pageKey.split("|");
  const title = titleRaw ?? "Untitled Page";
  const url = urlRaw ?? "";
  const pageId = `page-${slugify(`${title}-${url}`)}`;
  const lines: string[] = [];
  lines.push(`# ${title}`);
  lines.push("");
  lines.push(`Page ID: \`${pageId}\``);
  lines.push(`URL: ${url}`);
  lines.push("");

  lines.push(sectionHeader(2, "Overview"));
  lines.push("");
  lines.push(
    `Captured ${pageStates.length} state(s). Representative state: ${pageStates[0]?.id ?? "n/a"}.`
  );
  lines.push("");

  lines.push(sectionHeader(2, "Layout"));
  lines.push("");
  lines.push(
    pageStates[0]?.componentHints.length
      ? `Component hints: ${pageStates[0].componentHints.join(", ")}.`
      : "Layout hints unavailable."
  );
  lines.push("");

  lines.push(sectionHeader(2, "Components"));
  lines.push("");
  const componentHints = new Set<string>();
  for (const state of pageStates) {
    for (const hint of state.componentHints) {
      componentHints.add(hint);
    }
  }
  if (componentHints.size === 0) {
    lines.push("- No component hints extracted.");
  } else {
    for (const hint of [...componentHints].slice(0, 40)) {
      lines.push(`- ${hint}`);
    }
  }
  lines.push("");

  lines.push(sectionHeader(2, "Interactions"));
  lines.push("");
  const stateSet = new Set(pageStates.map((s) => s.id));
  const edgeRows = analysis.navigation_edges.filter(
    (edge) => stateSet.has(edge.fromStateId) || stateSet.has(edge.toStateId)
  );
  if (edgeRows.length === 0) {
    lines.push("- No interactions mapped for this page.");
  } else {
    for (const edge of edgeRows.slice(0, 60)) {
      lines.push(`- ${edge.fromStateId} --[${edge.actionLabel}]--> ${edge.toStateId}`);
    }
  }
  lines.push("");

  lines.push(sectionHeader(2, "Data Dependencies"));
  lines.push("");
  const relevantSchemas = analysis.normalized_schemas.slice(0, 10);
  if (relevantSchemas.length === 0) {
    lines.push("- None inferred.");
  } else {
    for (const schema of relevantSchemas) {
      lines.push(`- ${schema.entity}: ${schema.fields.length} fields`);
    }
  }
  lines.push("");

  lines.push(sectionHeader(2, "AI Touchpoints"));
  lines.push("");
  const aiItems = analysis.ai_response_maps.slice(0, 10);
  if (aiItems.length === 0) {
    lines.push("- No AI touchpoints found.");
  } else {
    for (const item of aiItems) {
      lines.push(`- Trigger "${item.trigger}" -> ${clampText(item.response, 120)}`);
    }
  }
  lines.push("");

  lines.push(sectionHeader(2, "Open Questions"));
  lines.push("");
  lines.push("- Are there hidden states requiring authenticated context?");
  lines.push("- Are there delayed/async transitions not captured in budget?");
  lines.push("");
  return lines.join("\n");
}

function renderRequirementsBacklog(items: RequirementItem[]): string {
  const lines = [sectionHeader(2, "Requirements Backlog"), ""];
  if (items.length === 0) {
    lines.push("No requirement items derived.");
    lines.push("");
    return lines.join("\n");
  }
  for (const item of items.slice(0, 80)) {
    lines.push(sectionHeader(3, item.title));
    lines.push("");
    lines.push(`ID: \`${item.id}\``);
    lines.push("");
    lines.push("Acceptance Criteria:");
    for (const criterion of item.acceptanceCriteria) {
      lines.push(`- ${criterion}`);
    }
    lines.push("Data Dependencies:");
    for (const dep of item.dataDependencies) {
      lines.push(`- ${dep}`);
    }
    lines.push(`Source States: ${item.sourceStateIds.join(", ") || "n/a"}`);
    lines.push("");
  }
  return lines.join("\n");
}

function renderDiagnostics(items: DiagnosticItem[]): string {
  const lines = [sectionHeader(2, "Diagnostics"), ""];
  if (items.length === 0) {
    lines.push("No diagnostics captured.");
    lines.push("");
    return lines.join("\n");
  }
  lines.push("| Time | Severity | Type | Message |");
  lines.push("| --- | --- | --- | --- |");
  for (const item of items.slice(0, 200)) {
    lines.push(
      `| ${fmtDateIso(item.timestamp)} | ${item.severity} | ${item.type} | ${clampText(item.message, 140).replace(/\|/g, "\\|")} |`
    );
  }
  lines.push("");
  return lines.join("\n");
}

function renderCoverageGaps(gaps: CoverageGap[]): string {
  const lines = [sectionHeader(2, "Coverage Gaps"), ""];
  if (gaps.length === 0) {
    lines.push("No explicit coverage gaps recorded.");
    lines.push("");
    return lines.join("\n");
  }
  for (const gap of gaps) {
    lines.push(`- [${gap.category}] ${gap.detail}`);
  }
  lines.push("");
  return lines.join("\n");
}

function renderAppendix(runDir: string, states: StateSummary[]): string {
  const lines = [sectionHeader(2, "Appendix (Artifacts)"), ""];
  lines.push(`Run directory: \`${runDir}\``);
  lines.push("");
  lines.push("| State | URL | Viewport Screenshot | Full Screenshot | HTML Snapshot |");
  lines.push("| --- | --- | --- | --- | --- |");
  for (const state of states.slice(0, 200)) {
    lines.push(
      `| ${state.id} | ${clampText(state.url, 80)} | ${state.screenshotViewport} | ${state.screenshotFull} | ${state.htmlSnapshot} |`
    );
  }
  lines.push("");
  return lines.join("\n");
}

export interface RenderedSpecs {
  indexMd: string;
  mergedSpecMd: string;
  pages: Array<{ fileName: string; content: string; title: string }>;
}

export function renderSpecs(analysis: AnalysisJson, runDir: string): RenderedSpecs {
  const groupedPages = groupStatesIntoPages(analysis.states);
  const pages: Array<{ fileName: string; content: string; title: string }> = [];
  for (const [key, pageStates] of groupedPages.entries()) {
    const [titleRaw, urlRaw] = key.split("|");
    const title = titleRaw ?? "Untitled";
    const url = urlRaw ?? "";
    const fileName = `${slugify(`${title}-${url}`)}.md`;
    pages.push({
      fileName,
      content: renderPageFileContent(key, pageStates, analysis),
      title,
    });
  }
  pages.sort((a, b) => a.fileName.localeCompare(b.fileName));

  const lines: string[] = [];
  lines.push("# Prototype Specification");
  lines.push("");
  lines.push(sectionHeader(2, "Executive Summary"));
  lines.push("");
  lines.push(
    `Captured ${analysis.states.length} states, ${analysis.navigation_edges.length} edges, ${analysis.extracted_snippets.length} extracted source snippets.`
  );
  lines.push("");
  lines.push(sectionHeader(2, "Run Metadata"));
  lines.push("");
  lines.push(`- Started: ${fmtDateIso(analysis.metadata.startedAt)}`);
  lines.push(`- Finished: ${analysis.metadata.finishedAt ? fmtDateIso(analysis.metadata.finishedAt) : "n/a"}`);
  lines.push(`- URL: ${analysis.metadata.url}`);
  lines.push(`- URL Hash: ${analysis.metadata.urlHash}`);
  lines.push(`- Tool Version: ${analysis.metadata.toolVersion}`);
  lines.push(`- Schema Version: ${analysis.metadata.schemaVersion}`);
  lines.push(`- Viewport: ${analysis.metadata.viewport.width}x${analysis.metadata.viewport.height}`);
  lines.push(`- Run Directory: ${runDir}`);
  lines.push("");
  lines.push(renderNavigationMap(analysis.states, analysis.navigation_edges));
  lines.push(renderDesignSystem(analysis.extracted_snippets));
  lines.push(renderSchemas(analysis.normalized_schemas));
  lines.push(renderFormulas(analysis.formulas, analysis.ai_response_maps, analysis.extracted_snippets));
  lines.push(sectionHeader(2, "Page Specs"));
  lines.push("");
  if (pages.length === 0) {
    lines.push("No page files generated.");
    lines.push("");
  } else {
    for (const page of pages) {
      lines.push(`- [${page.title}](pages/${page.fileName})`);
    }
    lines.push("");
  }
  lines.push(renderRequirementsBacklog(analysis.requirements_backlog));
  lines.push(renderDiagnostics(analysis.diagnostics));
  lines.push(renderCoverageGaps(analysis.coverage_gaps));
  lines.push(renderAppendix(runDir, analysis.states));
  const mergedSpecMd = `${lines.join("\n").trim()}\n`;

  const indexLines: string[] = [];
  indexLines.push("# Prototype Analysis Index");
  indexLines.push("");
  indexLines.push("- Merged spec: [spec.md](spec.md)");
  indexLines.push("- Page specs:");
  for (const page of pages) {
    indexLines.push(`  - [${page.title}](pages/${page.fileName})`);
  }
  indexLines.push("");
  indexLines.push("## Summary");
  indexLines.push("");
  indexLines.push(
    `States: ${analysis.states.length}, Actions: ${analysis.actions.length}, Snippets: ${analysis.extracted_snippets.length}`
  );
  indexLines.push("");
  const indexMd = `${indexLines.join("\n").trim()}\n`;

  return {
    indexMd,
    mergedSpecMd,
    pages,
  };
}
