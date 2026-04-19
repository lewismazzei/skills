import test from "node:test";
import assert from "node:assert/strict";

import { extractFromSources } from "../scripts/source-extract.js";

test("extractFromSources finds formulas and ai response maps", () => {
  const source = `
    const vendors = [{ name: "AWS", score: 88.8, tier: "ELITE" }];
    const roi = (acv * term) + implementationCost + (fte * maintenancePct);
    const responses = {
      "vendor risk": "Based on benchmark data, vendor risk is elevated."
    };
  `;
  const result = extractFromSources([
    {
      id: "s1",
      ref: "inline#1",
      content: source,
    },
  ]);

  assert.ok(result.snippets.length > 0);
  assert.ok(result.formulas.length > 0);
  assert.ok(result.aiMaps.length > 0);
});
