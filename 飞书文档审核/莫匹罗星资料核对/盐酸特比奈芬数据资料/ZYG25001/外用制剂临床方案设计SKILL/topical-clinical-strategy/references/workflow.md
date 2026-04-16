# Workflow

## Goal

Use this skill to turn product inputs into a structured China/FDA clinical development strategy for locally acting topical small-molecule products.

## Core Sequence

1. Confirm that the product is within scope.
2. Collect the minimum input set.
3. Read `references/source-map.md`.
4. Read `references/regulatory/china-core.md` and `references/regulatory/fda-core.md` as needed.
5. Read `references/regulatory/china-official-source-index.md` when China official-source provenance or current verification matters.
6. Read `references/cde-fda-differences.md` when both regions matter.
7. Read `references/regulatory/innovative-core.md` when innovative-drug methodology or early clinical pharmacology questions matter.
8. Read `references/innovative-topical-rules.md` when innovative-drug logic or proof-of-concept logic matters.
9. Read `references/early-phase-design-rules.md` when the user asks for detailed early study design.
10. Read `references/regulatory/china-innovative-methods.md` when China-side innovative-drug methods detail matters.
11. Read `references/psg-strategy.md` when PSG may matter.
12. Read `references/formulations/film-forming-solution.md` when the dosage form is a film-forming solution or other in-situ film-forming topical.
13. Read `references/clinicaltrials-strategy.md` when same-target or same-indication trial-design precedent matters.
14. Read `references/output-template.md`.
15. Read `references/synopsis-template.md` when a more detailed study-architecture answer is needed.
16. Read the relevant indication module under `references/indications/`.
17. Read `references/case-library/index.md` when a family-based routing shortcut would help a teammate or reviewer.
18. Read `references/review-cases/topical-fda-cases.md` when FDA precedent matters.
19. Read `references/failure-patterns.md` and `references/known-boundaries.md` as a pre-answer sanity check.
20. Read `references/worked-examples/index.md` when a similar demonstration case would help shape the answer.
21. Read `references/output-self-check.md` before finalizing the answer.
22. Decide whether official web search or registry search is required.
23. Build the development logic.
24. Output both conservative and aggressive paths.

## Scope Check

Stay within this skill when all of the following are true:

- The product is a skin-applied, locally acting small-molecule drug.
- The formulation is a cream, gel, ointment, lotion, liniment, spray, foam, or film-forming topical product.
- The task is to design or compare clinical development strategy, not to draft the full protocol text.
- The target market is China, the United States, or both.

If the user is really asking for a full protocol synopsis or protocol authoring task, use this skill to set strategy first, then draft the protocol separately.
If the user asks for an internal study synopsis rather than a full formal protocol, stay within this skill and use `references/synopsis-template.md`.

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

If raw China source files are not locally mirrored, continue with the repo-bundled reference cards plus official retrieval from `references/regulatory/china-official-source-index.md` when needed.

## Evidence Ladder

Use evidence in this order:

1. formal CDE/NMPA guidance and FDA guidance
2. FDA public review documents, review packages, labels
3. targeted supportive layers:
   - PSG for FDA topical technical expectations
   - ClinicalTrials.gov for same-target or same-indication design precedent
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

Registry search is recommended when:

- same-target or same-indication trial-design precedent is unclear
- the answer needs help with duration, comparator, endpoint timing, or extension-pattern judgment
- oral-to-topical projects lack direct topical precedent

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
   - spray / foam
   - film-forming solution or membrane-forming topical as a distinct dosage-form class
   - modified delivery or release
6. need for:
   - MUsT or max-use PK
   - PK bridge
   - exposure-response analysis
   - dose-ranging
   - long-term safety
7. early-package architecture:
   - healthy volunteers
   - patients
   - sequential healthy volunteers to patients
   - SAD
   - MAD
   - patient PK
   - integrated PK plus signal design

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

Default to the structure in `references/output-template.md`.

If the user explicitly asks for a more detailed study design, switch to `references/synopsis-template.md`.

For every key recommendation, include:

- evidence type
- evidence point
- applicability condition

Default to Chinese for the main answer unless the user asks otherwise.

If the user asks early-design detail, explicitly answer:

- whether healthy volunteers or patients should enter first
- whether SAD and MAD are needed
- what each early study is trying to solve
- what progression criterion moves the program forward

If the user asks for synopsis depth, also answer:

- study sequence
- study-level cohort or arm architecture
- key entry direction rather than full entry text
- risk-control points
- go/no-go gates

If the dosage form is film-forming, also answer:

- whether film formation materially changes local residence or systemic accumulation risk
- whether drying time, residue, secondary transfer, or peel-off behavior could affect study execution
- whether repeated-application PK should be prioritized over a larger classical SAD package

## Validation Use

Use `references/validation-prompts.md` for manual testing and future team trial runs.
Use `references/validation-results-round4.md` to understand what the first manual validation round already exposed.
Use `references/validation-results-round7.md` to understand release-prep and business-acceptance findings.
Use `references/validation-results-round10.md` to understand the three-scenario real-run validation findings.
Use `references/worked-examples/index.md` to align style and depth for representative scenarios.
Use `references/case-library/index.md` to route newer indication families for teammates or first-time users.
