import { parse } from "acorn";
import { fullAncestor } from "acorn-walk";

import type {
  AIResponseMap,
  ExtractedSnippet,
  FormulaSpec,
  NormalizedSchema,
} from "./types.js";
import { confidenceFromEvidence, hashOf, normalizeEntitySchema, stableId } from "./utils.js";

interface SourceBundle {
  id: string;
  ref: string;
  content: string;
}

function parseLiteralNode(node: unknown, depth = 0): unknown {
  if (!node || typeof node !== "object" || depth > 4) {
    return undefined;
  }
  const n = node as {
    type: string;
    value?: unknown;
    properties?: Array<{ key: { name?: string; value?: string }; value: unknown }>;
    elements?: unknown[];
  };
  if (n.type === "Literal") {
    return n.value;
  }
  if (n.type === "ObjectExpression") {
    const out: Record<string, unknown> = {};
    for (const prop of n.properties ?? []) {
      const key = prop.key.name ?? prop.key.value;
      if (!key) {
        continue;
      }
      out[key] = parseLiteralNode(prop.value, depth + 1);
    }
    return out;
  }
  if (n.type === "ArrayExpression") {
    return (n.elements ?? []).map((el) => parseLiteralNode(el, depth + 1));
  }
  return undefined;
}

function heuristicObjectArrays(source: string): Array<{ name: string; json: string; refLine: number }> {
  const matches: Array<{ name: string; json: string; refLine: number }> = [];
  const regex =
    /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(\[[\s\S]{20,1200}?\])\s*;/g;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(source))) {
    const name = m[1] ?? "unknown";
    const json = m[2] ?? "[]";
    const refLine = source.slice(0, m.index).split("\n").length;
    matches.push({ name, json, refLine });
  }
  return matches;
}

function heuristicFormulas(source: string): Array<{ expression: string; line: number }> {
  const out: Array<{ expression: string; line: number }> = [];
  const lines = source.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]?.trim() ?? "";
    if (!line || line.length > 240) {
      continue;
    }
    if (!/[+\-*/]/.test(line) || !/=/.test(line)) {
      continue;
    }
    if (!/(score|roi|cost|value|weight|term|fte|contract|implementation)/i.test(line)) {
      continue;
    }
    out.push({ expression: line.replace(/;$/, ""), line: i + 1 });
  }
  return out.slice(0, 60);
}

function heuristicAiMaps(source: string): Array<{ trigger: string; response: string; line: number }> {
  const out: Array<{ trigger: string; response: string; line: number }> = [];
  const objectRegex =
    /['"]([A-Za-z0-9 _-]{2,40})['"]\s*:\s*['"]([^'"]{20,400})['"]/g;
  let m: RegExpExecArray | null;
  while ((m = objectRegex.exec(source))) {
    const trigger = (m[1] ?? "").trim();
    const response = (m[2] ?? "").trim();
    if (!trigger || !response) {
      continue;
    }
    if (
      /(ai|ask|response|insight|recommend|risk|opportunity|vendor|market|score)/i.test(
        trigger
      ) ||
      /(analysis|insight|recommend|risk|opportunity|should|based on)/i.test(response)
    ) {
      const line = source.slice(0, m.index).split("\n").length;
      out.push({ trigger, response, line });
    }
  }
  return out.slice(0, 120);
}

function extractDesignTokens(source: string): Array<{ token: string; value: string; line: number }> {
  const out: Array<{ token: string; value: string; line: number }> = [];
  const cssVarRegex = /(--[a-zA-Z0-9-_]+)\s*:\s*([^;}{]+);/g;
  let m: RegExpExecArray | null;
  while ((m = cssVarRegex.exec(source))) {
    const token = m[1] ?? "";
    const value = (m[2] ?? "").trim();
    if (!token || !value) {
      continue;
    }
    const line = source.slice(0, m.index).split("\n").length;
    out.push({ token, value, line });
  }
  return out.slice(0, 200);
}

function extractGamification(source: string): Array<{ snippet: string; line: number }> {
  const out: Array<{ snippet: string; line: number }> = [];
  const lines = source.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i] ?? "";
    if (/(insight score|unlock|blur|contrib|points|gamification|badge|level)/i.test(line)) {
      out.push({ snippet: line.trim(), line: i + 1 });
    }
  }
  return out.slice(0, 120);
}

function extractNavigationHooks(source: string): Array<{ snippet: string; line: number }> {
  const out: Array<{ snippet: string; line: number }> = [];
  const lines = source.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i] ?? "";
    if (/(data-page|openModal|showModal|toggle|onclick|navigate|route|router)/i.test(line)) {
      out.push({ snippet: line.trim(), line: i + 1 });
    }
  }
  return out.slice(0, 200);
}

function extractAstObjectArrays(
  source: string,
  sourceRef: string
): Array<{ name: string; samples: Array<Record<string, unknown>>; sourceRef: string }> {
  const models: Array<{ name: string; samples: Array<Record<string, unknown>>; sourceRef: string }> = [];
  try {
    const ast = parse(source, {
      ecmaVersion: "latest",
      sourceType: "script",
      allowHashBang: true,
    });
    fullAncestor(ast as never, (node, _state, ancestors) => {
      if (node.type !== "VariableDeclarator" || !node.init || !node.id) {
        return;
      }
      if (node.id.type !== "Identifier") {
        return;
      }
      if (node.init.type !== "ArrayExpression") {
        return;
      }
      const parsed = parseLiteralNode(node.init);
      if (!Array.isArray(parsed)) {
        return;
      }
      const objectItems = parsed.filter(
        (item): item is Record<string, unknown> => !!item && typeof item === "object" && !Array.isArray(item)
      );
      if (objectItems.length === 0) {
        return;
      }
      const hasInterestingKeys = objectItems.some((obj) =>
        Object.keys(obj).some((k) => /(id|name|score|tier|cost|roi|weight|value|vendor)/i.test(k))
      );
      if (!hasInterestingKeys) {
        return;
      }
      const line = (node as { start: number }).start;
      const lineNo = source.slice(0, line).split("\n").length;
      let parentFn:
        | { type: string; id?: { name?: string } | null }
        | undefined;
      for (let i = ancestors.length - 1; i >= 0; i -= 1) {
        const candidate = ancestors[i];
        if (!candidate) {
          continue;
        }
        if (
          candidate.type === "FunctionDeclaration" ||
          candidate.type === "FunctionExpression"
        ) {
          parentFn = candidate as { type: string; id?: { name?: string } | null };
          break;
        }
      }
      const scopedName =
        parentFn && "id" in parentFn && parentFn.id && "name" in parentFn.id
          ? `${node.id.name}@${parentFn.id.name}`
          : node.id.name;
      models.push({
        name: scopedName,
        samples: objectItems.slice(0, 50),
        sourceRef: `${sourceRef}:L${lineNo}`,
      });
    });
  } catch {
    return [];
  }
  return models;
}

export interface ExtractionResult {
  snippets: ExtractedSnippet[];
  schemas: NormalizedSchema[];
  formulas: FormulaSpec[];
  aiMaps: AIResponseMap[];
}

export function extractFromSources(sources: SourceBundle[]): ExtractionResult {
  const snippets: ExtractedSnippet[] = [];
  const schemas: NormalizedSchema[] = [];
  const formulas: FormulaSpec[] = [];
  const aiMaps: AIResponseMap[] = [];

  for (const source of sources) {
    const astModels = extractAstObjectArrays(source.content, source.ref);
    for (const model of astModels) {
      const schema = normalizeEntitySchema(model.name, model.samples, [model.sourceRef]);
      schemas.push(schema);
      snippets.push({
        id: stableId("snippet", `${source.id}:ast:${model.name}`),
        category: "data-model",
        title: `Data model: ${model.name}`,
        content: JSON.stringify(model.samples.slice(0, 3), null, 2),
        sourceRef: model.sourceRef,
        method: "ast",
        confidence: confidenceFromEvidence({ runtimeObserved: false, sourceRefs: 1 }),
      });
    }

    const heuristicModels = heuristicObjectArrays(source.content);
    for (const model of heuristicModels) {
      snippets.push({
        id: stableId("snippet", `${source.id}:heuristic-model:${model.name}:${model.refLine}`),
        category: "data-model",
        title: `Heuristic model candidate: ${model.name}`,
        content: model.json.slice(0, 1000),
        sourceRef: `${source.ref}:L${model.refLine}`,
        method: "heuristic",
        confidence: "medium",
      });
    }

    const formulaCandidates = heuristicFormulas(source.content);
    for (const formula of formulaCandidates) {
      const vars = [...new Set(formula.expression.match(/[A-Za-z_][A-Za-z0-9_]*/g) ?? [])].slice(
        0,
        4
      );
      const sampleInputs: Record<string, number> = {};
      for (let i = 0; i < vars.length; i += 1) {
        const variable = vars[i];
        if (!variable) {
          continue;
        }
        sampleInputs[variable] = i + 2;
      }
      let expectedOutput = 0;
      if (vars.length > 0) {
        const arithmetic = formula.expression.split("=").at(-1) ?? "0";
        const replaced = vars.reduce(
            (acc, variable) =>
              acc.replaceAll(
                new RegExp(`\\b${variable}\\b`, "g"),
                String(sampleInputs[variable] ?? 0)
              ),
            arithmetic
        );
        if (/^[0-9+\-*/().\s]+$/.test(replaced)) {
          try {
            // eslint-disable-next-line no-new-func
            const value = Function(`"use strict"; return (${replaced});`)() as number;
            if (Number.isFinite(value)) {
              expectedOutput = Number(value.toFixed(4));
            }
          } catch {
            expectedOutput = 0;
          }
        }
      }

      const spec: FormulaSpec = {
        id: stableId("formula", `${source.id}:${formula.line}:${formula.expression}`),
        name: formula.expression.split("=")[0]?.trim() || `Formula ${formula.line}`,
        expression: formula.expression,
        evidence: `${source.ref}:L${formula.line}`,
        method: "heuristic",
        confidence: confidenceFromEvidence({ runtimeObserved: false, sourceRefs: 1 }),
        examples: [
          {
            expression: formula.expression,
            sampleInputs,
            expectedOutput,
          },
        ],
      };
      formulas.push(spec);
      snippets.push({
        id: stableId("snippet", `${spec.id}:formula`),
        category: "formula",
        title: spec.name,
        content: spec.expression,
        sourceRef: spec.evidence,
        method: spec.method,
        confidence: spec.confidence,
      });
    }

    const aiCandidates = heuristicAiMaps(source.content);
    for (const mapping of aiCandidates) {
      const id = stableId("aimap", `${source.id}:${mapping.line}:${mapping.trigger}`);
      const item: AIResponseMap = {
        id,
        trigger: mapping.trigger,
        response: mapping.response,
        sourceRef: `${source.ref}:L${mapping.line}`,
        method: "heuristic",
        confidence: confidenceFromEvidence({ runtimeObserved: false, sourceRefs: 1 }),
      };
      aiMaps.push(item);
      snippets.push({
        id: stableId("snippet", `${id}:ai`),
        category: "ai-response-map",
        title: `AI mapping: ${mapping.trigger}`,
        content: mapping.response,
        sourceRef: item.sourceRef,
        method: item.method,
        confidence: item.confidence,
      });
    }

    const tokenCandidates = extractDesignTokens(source.content);
    for (const token of tokenCandidates) {
      snippets.push({
        id: stableId("snippet", `${source.id}:token:${token.token}:${token.line}`),
        category: "design-token",
        title: token.token,
        content: token.value,
        sourceRef: `${source.ref}:L${token.line}`,
        method: "heuristic",
        confidence: "high",
      });
    }

    const gameCandidates = extractGamification(source.content);
    for (const g of gameCandidates) {
      snippets.push({
        id: stableId("snippet", `${source.id}:game:${g.line}:${hashOf(g.snippet)}`),
        category: "gamification",
        title: "Gamification signal",
        content: g.snippet,
        sourceRef: `${source.ref}:L${g.line}`,
        method: "heuristic",
        confidence: "medium",
      });
    }

    const hooks = extractNavigationHooks(source.content);
    for (const h of hooks) {
      snippets.push({
        id: stableId("snippet", `${source.id}:hook:${h.line}:${hashOf(h.snippet)}`),
        category: "navigation-hook",
        title: "Navigation or modal hook",
        content: h.snippet,
        sourceRef: `${source.ref}:L${h.line}`,
        method: "heuristic",
        confidence: "medium",
      });
    }
  }

  const dedupeBy = <T extends { id: string }>(items: T[]): T[] => {
    const byId = new Map<string, T>();
    for (const item of items) {
      if (!byId.has(item.id)) {
        byId.set(item.id, item);
      }
    }
    return [...byId.values()];
  };

  return {
    snippets: dedupeBy(snippets),
    schemas: dedupeBy(
      schemas.map((schema) => ({
        ...schema,
        id: stableId("schema", `${schema.entity}:${schema.sourceRefs.join(",")}`),
      })) as Array<NormalizedSchema & { id: string }>
    ).map(({ id: _id, ...schema }) => schema),
    formulas: dedupeBy(formulas),
    aiMaps: dedupeBy(aiMaps),
  };
}
