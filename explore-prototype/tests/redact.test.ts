import test from "node:test";
import assert from "node:assert/strict";

import { redactText } from "../scripts/utils.js";
import type { RedactionEvent } from "../scripts/types.js";

test("redactText masks sensitive patterns and records events", () => {
  const events: RedactionEvent[] = [];
  const input =
    "Contact me at user@example.com, use sk_live_1234567890abcdef, SSN 123-45-6789";
  const out = redactText(input, events, true);
  assert.match(out, /\[REDACTED_EMAIL\]/);
  assert.match(out, /\[REDACTED_API_KEY\]/);
  assert.match(out, /\[REDACTED_SSN\]/);
  assert.ok(events.length >= 3);
});

test("redactText no-op when disabled", () => {
  const events: RedactionEvent[] = [];
  const input = "user@example.com";
  const out = redactText(input, events, false);
  assert.equal(out, input);
  assert.equal(events.length, 0);
});
