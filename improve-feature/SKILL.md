---
name: improve-feature
description: Improve a feature across iterations after producing an artifact where the first attempt is unlikely to be the best one. Use after building a UI, component, API, or flow to define the bar, measure the current state, fix the highest-impact problem, and re-measure until it meets the bar or gains flatten.
---

# Iterate

The first version is a draft. Your job is the loop that follows.

## 1. Define The Bar

Before improving anything, write down how this artifact will be judged:

- Visual -> a 1-5 rubric covering hierarchy, contrast, type scale, spacing, CTA clarity, trust signals, and whether it looks generic. Always screenshot at a fixed viewport.
- Performance -> one measurable metric, such as p50 latency in ms, plus a benchmark that prints it and a test suite that pins correct behavior.
- Flow / interactive -> a concrete task to complete. Success means the artifact can be used end-to-end without confusion. Drive it with browser or computer use, not a glance.

## 2. Measure The Current State

Run it and capture evidence, such as a screenshot, benchmark number, or walkthrough recording.
Write down the top problems, ranked by impact.

## 3. Change One Thing

Fix only the highest-impact problem this pass. Do not refactor opportunistically.

## 4. Re-measure And Gate

Re-capture the same evidence at the same settings.

- Keep the change only if it improved the bar and broke no guardrail, with tests staying green.
- Otherwise revert and try the next hypothesis.

## 5. Stop Deliberately

Stop when you meet the bar, run out of budget, or gains flatten. Cap the number of passes.
Keep a short changelog: what was wrong, what changed, and before -> after.
