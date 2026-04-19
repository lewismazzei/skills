export type Confidence = "high" | "medium" | "low";

export type ExtractionMethod = "runtime" | "heuristic" | "ast" | "inferred";

export interface CliOptions {
  url: string;
  outDir?: string;
  yes: boolean;
  overwrite: boolean;
  safeMode: boolean;
  dryRun: boolean;
  mobile: boolean;
  storageState?: string;
  fetchCrossOriginScripts: boolean;
  allowedOrigins: string[];
  maxMinutes: number;
  maxStates: number;
  maxActions: number;
  maxDepth: number;
  maxPages: number;
  maxActionsPerState: number;
  focus: string[];
  fixturesPath?: string;
  allowSensitiveOutput: boolean;
  mergedSpec: boolean;
  userAgent?: string;
}

export interface RunPaths {
  runDir: string;
  pagesDir: string;
  screenshotsDir: string;
  htmlDir: string;
}

export interface RunMetadata {
  schemaVersion: string;
  toolVersion: string;
  startedAt: string;
  finishedAt?: string;
  durationMs?: number;
  cwd: string;
  url: string;
  urlHash: string;
  outDir: string;
  runDir: string;
  flags: Record<string, string | number | boolean | string[]>;
  viewport: {
    width: number;
    height: number;
    mobile: boolean;
  };
  userAgent: string;
  nodeVersion: string;
  platform: string;
}

export interface ActionTarget {
  id: string;
  type: "click" | "fill" | "select" | "toggle" | "submit";
  selector: string;
  label: string;
  confidence: Confidence;
  hints: {
    tag: string;
    href?: string;
    role?: string;
    onclick?: string;
    inputType?: string;
  };
}

export interface StateSummary {
  id: string;
  url: string;
  title: string;
  fingerprint: string;
  depth: number;
  actionPath: string[];
  discoveredAt: string;
  screenshotViewport: string;
  screenshotFull: string;
  modalScreenshots: string[];
  htmlSnapshot: string;
  componentHints: string[];
  textSnippet: string;
}

export interface NavigationEdge {
  fromStateId: string;
  toStateId: string;
  actionId: string;
  actionLabel: string;
}

export interface DiagnosticItem {
  type: "console-error" | "console-warning" | "request-failed" | "info";
  message: string;
  url?: string;
  timestamp: string;
  severity: "high" | "medium" | "low";
}

export interface RedactionEvent {
  category:
    | "api-key"
    | "email"
    | "phone"
    | "ssn-like"
    | "token"
    | "authorization";
  sample: string;
}

export interface ExtractedSnippet {
  id: string;
  category:
    | "data-model"
    | "formula"
    | "ai-response-map"
    | "design-token"
    | "gamification"
    | "navigation-hook";
  title: string;
  content: string;
  sourceRef: string;
  method: ExtractionMethod;
  confidence: Confidence;
}

export interface SchemaField {
  name: string;
  inferredType: string;
  required: boolean;
  example: string;
}

export interface NormalizedSchema {
  entity: string;
  fields: SchemaField[];
  sampleCount: number;
  sourceRefs: string[];
}

export interface FormulaExample {
  expression: string;
  sampleInputs: Record<string, number>;
  expectedOutput: number;
}

export interface FormulaSpec {
  id: string;
  name: string;
  expression: string;
  evidence: string;
  method: ExtractionMethod;
  confidence: Confidence;
  examples: FormulaExample[];
}

export interface AIResponseMap {
  id: string;
  trigger: string;
  response: string;
  sourceRef: string;
  method: ExtractionMethod;
  confidence: Confidence;
}

export interface CoverageGap {
  id: string;
  category: "budget" | "auth" | "blocked-action" | "script-skip" | "parsing";
  detail: string;
}

export interface RequirementItem {
  id: string;
  title: string;
  acceptanceCriteria: string[];
  dataDependencies: string[];
  sourceStateIds: string[];
}

export interface AnalysisJson {
  schema_version: string;
  metadata: RunMetadata;
  states: StateSummary[];
  actions: ActionTarget[];
  navigation_edges: NavigationEdge[];
  diagnostics: DiagnosticItem[];
  extracted_snippets: ExtractedSnippet[];
  normalized_schemas: NormalizedSchema[];
  formulas: FormulaSpec[];
  ai_response_maps: AIResponseMap[];
  requirements_backlog: RequirementItem[];
  coverage_gaps: CoverageGap[];
  redaction_report: {
    enabled: boolean;
    events: RedactionEvent[];
  };
}

export interface DiscoveredAction {
  action: ActionTarget;
  selector: string;
}

export interface FixtureInput {
  defaults?: Record<string, string | number | boolean>;
}
