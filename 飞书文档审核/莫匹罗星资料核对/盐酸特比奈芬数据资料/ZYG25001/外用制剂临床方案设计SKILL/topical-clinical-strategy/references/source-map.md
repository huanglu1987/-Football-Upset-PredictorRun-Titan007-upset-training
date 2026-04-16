# Source Map

## Purpose

Use this file to decide which sources to consult first and which sources require live official browsing.

## Repo-Bundled Core Sources

These repo files are the primary knowledge base for normal skill use and should be available to any teammate who downloads the repository.

### Skill QA and Support References

- `references/psg-strategy.md`
- `references/innovative-topical-rules.md`
- `references/early-phase-design-rules.md`
- `references/clinicaltrials-strategy.md`
- `references/failure-patterns.md`
- `references/known-boundaries.md`
- `references/synopsis-template.md`
- `references/validation-prompts.md`
- `references/output-self-check.md`
- `references/validation-results-round4.md`
- `references/validation-results-round7.md`
- `references/validation-results-round10.md`
- `references/worked-examples/index.md`
- `references/case-library/index.md`

### China Core Guidance

- `references/regulatory/china-core.md`
- `references/regulatory/china-official-source-index.md`
- `references/regulatory/innovative-core.md`
- `references/regulatory/china-innovative-methods.md`

### Useful China Supporting Sources

- `references/innovative-topical-rules.md`
- `references/regulatory/china-official-source-index.md`
- `references/regulatory/innovative-core.md`
- `references/regulatory/china-innovative-methods.md`

### FDA Case Summary Source

- `references/review-cases/topical-fda-cases.md`

Use this repo summary as the practical precedent layer. A separate author-local structured CSV once informed parts of the summary, but it is not required for normal skill use or public distribution.

## Official Online Sources

Browse these when the task requires current FDA or CDE support.

### FDA Guidance and Approval Sources

- FDA guidance portal: `https://www.fda.gov/regulatory-information/search-fda-guidance-documents`
- PSG portal: `https://www.fda.gov/drugs/guidances-drugs/product-specific-guidances-generic-drug-development`
- Drugs@FDA and review docs: `https://www.accessdata.fda.gov/scripts/cder/daf/`
- Review package host: `https://www.accessdata.fda.gov/drugsatfda_docs/`
- ClinicalTrials.gov: `https://clinicaltrials.gov/`

### China Official Sources

- CDE portal: `https://www.cde.org.cn/`
- NMPA portal: `https://www.nmpa.gov.cn/`

## Source Roles

### Tier 1: Core Rules

Use for the default rule tree.

- CDE/NMPA guidance
- FDA general guidance
- `references/regulatory/china-core.md`
- `references/regulatory/china-official-source-index.md`
- `references/regulatory/fda-core.md`

### Tier 2: Review Practice

Use to understand what FDA actually accepted in public cases.

- public reviews
- multidisciplinary reviews
- labels
- review packages
- curated 505(b)(2) case summaries
- `references/review-cases/topical-fda-cases.md`

### Tier 3: Supportive Technical Layer

Use to refine topical formulation logic, especially when discussing complex external products.

- PSG
- topical BE logic
- Q1/Q2/Q3 and IVRT/IVPT concepts
- innovative-topical proof-of-concept and early clinical pharmacology logic
- `ClinicalTrials.gov` when same-target or same-indication design precedent matters
- `references/cde-fda-differences.md`
- `references/psg-strategy.md`
- `references/innovative-topical-rules.md`
- `references/early-phase-design-rules.md`
- `references/clinicaltrials-strategy.md`
- `references/synopsis-template.md`

### Tier 4: Skill QA Layer

Use to keep answers stable and testable.

- `references/failure-patterns.md`
- `references/known-boundaries.md`
- `references/validation-prompts.md`
- `references/output-self-check.md`
- `references/validation-results-round4.md`
- `references/validation-results-round7.md`
- `references/worked-examples/index.md`

## Team-Download Note

For teammate-friendly usage after downloading the repo:

- start from `references/case-library/index.md` if the user wants the closest family pattern quickly
- use `references/output-template.md` for strategy mode
- use `references/synopsis-template.md` for internal study-architecture drafting

## Live-Browse Triggers

Search official sources when:

- the user asks for FDA strategy
- the user asks what is current or latest
- PSG is material to the answer
- a specific product is cited
- the user asks how innovative-drug early studies should be designed
- the answer needs links or direct source attribution

## Registry Query Triggers

Search `ClinicalTrials.gov` when:

- same-target or same-indication design precedent is unclear
- the answer needs help with endpoint timing, duration, or comparator patterns
- oral-to-topical projects lack direct topical precedent
- the user explicitly asks about same-target or same-class trial designs

## High-Value FDA Topical Review Examples

These examples are worth checking when relevant:

- Hyftor
- Zilxi
- Twyneo
- Epsolay
- Cabtreo

Use them to study:

- max-use PK / MUsT logic
- bridge strategy
- long-term safety expectations
- endpoint acceptability
- wording around benefit-risk and waiver requests

## Current Indication Modules

Always read the matching indication module for:

- acne
- rosacea
- superficial fungal infection
- AGA
- atopic dermatitis
- plaque psoriasis
- seborrheic dermatitis

The first four modules currently have the deepest worked-example support. The newer three expanded modules should still be used, but may rely more heavily on current official browsing and general-rule interpretation.

Then add official browsing if the user asks for FDA or current position.
