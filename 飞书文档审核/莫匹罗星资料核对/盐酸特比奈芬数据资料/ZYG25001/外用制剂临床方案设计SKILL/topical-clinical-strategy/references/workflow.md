# Workflow

## Goal

Use this skill to turn product inputs into a structured China/FDA clinical development strategy for locally acting topical small-molecule products.

## Core Sequence

1. Confirm that the product is within scope.
2. Collect the minimum input set.
3. Read `references/source-map.md`.
4. Read `references/regulatory/china-core.md` and `references/regulatory/fda-core.md` as needed.
5. Read `references/cde-fda-differences.md` when both regions matter.
6. Read `references/output-template.md`.
7. Read the relevant indication module under `references/indications/`.
8. Read `references/review-cases/topical-fda-cases.md` when FDA precedent matters.
9. Decide whether official web search is required.
10. Build the development logic.
11. Output both conservative and aggressive paths.

## Scope Check

Stay within this skill when all of the following are true:

- The product is a skin-applied, locally acting small-molecule drug.
- The formulation is a cream, gel, ointment, lotion, liniment, spray, foam, or film-forming topical product.
- The task is to design or compare clinical development strategy, not to draft the full protocol text.
- The target market is China, the United States, or both.

If the user is really asking for a full protocol synopsis or protocol authoring task, use this skill to set strategy first, then draft the protocol separately.

## Required Inputs

If the user does not provide all fields, gather or infer the minimum set using `references/input-template.md`.

At minimum, resolve:

- active ingredient
- dosage form
- target concentration or strength
- target indication
- target population
- target region
- initial registration-path guess
- available preclinical or early clinical evidence

Do not stop solely because the target concentration lacks prior topical precedent. Treat that as a non-blocking risk signal and adjust the conservative path accordingly.

## Evidence Ladder

Use evidence in this order:

1. formal CDE/NMPA guidance and FDA guidance
2. FDA public review documents, review packages, labels
3. PSG
4. curated case summaries
5. general development logic

If lower-tier evidence conflicts with higher-tier evidence, follow the higher tier and explain the lower-tier item as a practical signal rather than a rule.

## When to Browse Official Sources

Official web search is mandatory when any of the following is true:

- the user asks about FDA
- the user asks for the latest or current position
- the output relies on PSG
- a specific approved product, review package, or label is discussed
- the output needs direct citations or links

When browsing, prefer official sources only:

- `fda.gov`
- `accessdata.fda.gov`
- `cde.org.cn`
- `nmpa.gov.cn`

## Strategy Logic

After collecting inputs and sources, make these judgments in order:

1. region: China, US, or both
2. registration type: innovative, improved new drug, or uncertain
3. existing knowledge base:
   - same ingredient oral precedent
   - same ingredient topical precedent
   - same indication standard of care
   - similar FDA review precedent
4. systemic exposure risk:
   - negligible
   - low but relevant
   - potentially meaningful
5. formulation complexity:
   - conventional semisolid
   - spray / foam / film-forming
   - modified delivery or release
6. need for:
   - MUsT or max-use PK
   - PK bridge
   - exposure-response analysis
   - dose-ranging
   - long-term safety

## Conservative vs Aggressive Paths

Always output both.

### Conservative Path

Prefer this when:

- formulation change is meaningful
- systemic exposure is uncertain
- concentration rationale is weak
- cross-product bridging is fragile
- the plan must minimize regulatory risk

### Aggressive Path

Prefer this when:

- same-ingredient or strong class precedent exists
- systemic exposure is expected to be very low
- bridge logic is credible
- the user is willing to accept greater regulatory uncertainty

## Hard Limits

Do not present false certainty.

Avoid statements such as:

- “must run exactly two Phase 3 studies” when evidence is weak
- “long-term safety can definitely be waived” without a clear basis
- “PSG requires this for 505(b)(2)” without clarifying that PSG is supportive rather than determinative

## Special Rule for Target Strength Uncertainty

If the target strength lacks established topical precedent:

- do not stop
- explain why the strength is still analyzable
- state whether the rationale comes from oral exposure, class knowledge, preclinical efficacy, local exposure logic, or a pure development hypothesis
- make the conservative path more exploration-heavy

## Output Discipline

Use the structure in `references/output-template.md`.

For every key recommendation, include:

- evidence type
- evidence point
- applicability condition

Default to Chinese for the main answer unless the user asks otherwise.
