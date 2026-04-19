import test from "node:test";
import assert from "node:assert/strict";

import { hashOf, stableId } from "../scripts/utils.js";

test("hashOf is deterministic", () => {
  const a = hashOf("hello-world");
  const b = hashOf("hello-world");
  assert.equal(a, b);
  assert.equal(a.length, 16);
});

test("stableId includes prefix", () => {
  const id = stableId("state", "example");
  assert.match(id, /^state-[a-f0-9]{16}$/);
});
