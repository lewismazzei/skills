import test from "node:test";
import assert from "node:assert/strict";

import { normalizeEntitySchema } from "../scripts/utils.js";

test("normalizeEntitySchema infers field metadata", () => {
  const schema = normalizeEntitySchema(
    "vendors",
    [
      { id: 1, name: "AWS", score: 88.8, tier: "ELITE" },
      { id: 2, name: "Azure", score: 86.2, tier: "LEADER" },
    ],
    ["inline:1"]
  );

  assert.equal(schema.entity, "vendors");
  assert.equal(schema.sampleCount, 2);
  assert.ok(schema.fields.find((f) => f.name === "id"));
  assert.ok(schema.fields.find((f) => f.name === "score"));
  assert.ok(schema.fields.every((f) => f.required));
});
