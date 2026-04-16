---
name: topical-clinical-strategy
description: Design China and FDA clinical development strategies for locally acting topical small-molecule products such as creams, gels, ointments, lotions, sprays, foams, and film-forming products. Use when Codex needs to assess innovative vs improved new-drug paths, compare conservative and aggressive development routes, judge MUsT/max-use PK or bridge needs, or structure Phase 1-3 strategy for indications including acne, rosacea, superficial fungal infection, androgenetic alopecia, atopic dermatitis, plaque psoriasis, and seborrheic dermatitis.
---

# Topical Clinical Strategy

## Overview

Use this skill to turn product inputs into a structured clinical-development strategy for skin-applied, locally acting small-molecule drugs in China, the United States, or both. Default to strategy-level output with clear rationale, not full protocol drafting.

## Workflow

1. Normalize the request with `references/input-template.md` if the user input is incomplete.
2. Read `references/source-map.md` to choose the right evidence layer.
3. Read `references/regulatory/china-core.md` and `references/regulatory/fda-core.md` as needed.
4. Read `references/cde-fda-differences.md` when both regions matter.
5. Read `references/innovative-topical-rules.md` when innovative-drug logic or true proof-of-concept logic matters.
6. Read `references/output-template.md` before drafting the answer.
7. Read `references/clinicaltrials-strategy.md` when same-target or same-indication trial-design precedent matters.
8. Read the matching indication module under `references/indications/`.
9. Read `references/review-cases/topical-fda-cases.md` when FDA precedent matters.
10. Read `references/known-boundaries.md` before finalizing the answer.
11. Build the strategy using the decision sequence below.
12. Output both conservative and aggressive paths.

## Decision Sequence

Make these judgments in order:

1. region: China, US, or both
2. registration type: innovative, improved new drug, or uncertain
3. existing knowledge base:
   - same ingredient oral precedent
   - same ingredient topical precedent
   - same indication standard of care
   - relevant FDA public review precedent
4. systemic exposure risk
5. formulation complexity and local-delivery change
6. need for:
   - max-use PK / MUsT
   - PK bridge
   - exposure-response analysis
   - dose-ranging
   - long-term safety
7. confirmatory evidence strength
8. conservative vs aggressive route selection

## Evidence Rules

Use evidence in this order:

1. formal CDE/NMPA and FDA guidance
2. FDA public reviews, labels, review packages
3. targeted supportive layers:
   - PSG for FDA topical technical expectations
   - ClinicalTrials.gov for same-target or same-indication design precedent
4. curated case summaries
5. general development logic

If sources conflict, follow the higher-tier source and explain the lower-tier item as supportive practice rather than a rule.

## When to Browse Official Sources

Browse official sources when:

- the user asks for FDA strategy
- the user asks about the latest or current position
- PSG materially affects the answer
- a specific approved product, review package, or label is discussed
- the answer needs direct source links

Restrict browsing to official sources when possible:

- `fda.gov`
- `accessdata.fda.gov`
- `cde.org.cn`
- `nmpa.gov.cn`

Search `ClinicalTrials.gov` when:

- same-target or same-indication trial-design precedent is unclear
- oral-to-topical projects lack direct topical precedent
- the answer needs help with comparator, duration, endpoint timing, or long-term extension patterns

## Output Rules

- Always provide both conservative and aggressive paths unless the user explicitly asks for only one.
- Keep the main answer at the clinical-development-strategy level.
- For each key recommendation, state:
  - evidence type
  - evidence point
  - applicability condition
- Default to Chinese unless the user asks otherwise.

## Special Handling

- Do not stop solely because the target strength lacks prior topical precedent.
- Treat missing topical-strength precedent as a non-blocking risk signal.
- If author-local raw source files listed in the source map are missing, continue with repo-bundled cards and official browsing instead of blocking.
- If the user input is sparse, still produce a first-pass strategy and clearly mark uncertainty.
- If the question drifts into full protocol drafting, use this skill to settle the strategy first and only then expand into protocol-level detail.

## References

Read these as needed:

- `references/workflow.md`
- `references/source-map.md`
- `references/input-template.md`
- `references/output-template.md`
- `references/output-self-check.md`
- `references/psg-strategy.md`
- `references/innovative-topical-rules.md`
- `references/clinicaltrials-strategy.md`
- `references/failure-patterns.md`
- `references/known-boundaries.md`
- `references/validation-prompts.md`
- `references/validation-results-round4.md`
- `references/validation-results-round7.md`
- `references/worked-examples/index.md`
- `references/regulatory/china-core.md`
- `references/regulatory/fda-core.md`
- `references/cde-fda-differences.md`
- `references/review-cases/topical-fda-cases.md`
- `references/indications/acne.md`
- `references/indications/rosacea.md`
- `references/indications/superficial-fungal.md`
- `references/indications/aga.md`
- `references/indications/ad.md`
- `references/indications/psoriasis.md`
- `references/indications/seborrheic-dermatitis.md`
