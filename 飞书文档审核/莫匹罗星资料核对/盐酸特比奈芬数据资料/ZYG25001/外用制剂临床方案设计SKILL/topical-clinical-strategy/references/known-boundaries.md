# Known Boundaries

## Purpose

Use this file to keep the skill honest. It defines where the current version is strong, where it is only moderately reliable, and where it should not over-claim.

## Strong-Fit Scenarios

The current version is strongest when:

- the product is a skin-applied, locally acting small-molecule drug
- the dosage form is a cream, gel, ointment, lotion, liniment, spray, foam, or film-forming product
- the user wants strategy-level China, FDA, or dual-region development advice
- the indication is one of the current seven modules:
  - acne
  - rosacea
  - superficial fungal infection
  - AGA
  - atopic dermatitis
  - plaque psoriasis
  - seborrheic dermatitis

The first four modules still have the deepest precedent and worked-example support. The newer three modules are useful now, but they remain somewhat more dependent on general-rule interpretation and current official browsing.

## Moderate-Fit Scenarios

The skill can still help, but answers should usually stay in first-pass strategy mode, when:

- the indication is outside the current seven modules
- the formulation is within scope but highly novel in delivery behavior
- the active ingredient has only oral precedent and little topical history
- the target strength is largely hypothesis-driven

The skill can also help with innovative-topical projects, but innovative-drug case precedent is still shallower than improved-new-drug precedent.

## Current Hard Boundaries

Do not present this skill as a finished solution for:

- transdermal systemic products or patches
- biologics, peptides, nucleic acids, cell therapies, or device-led products
- ophthalmic, nasal, oral-mucosal, or vaginal products outside the current skin-topical scope
- full protocol authoring, full SAP writing, or exact sample-size calculation
- CMC equivalence packages or deep formulation-comparability work

## Evidence Boundaries

Keep these distinctions explicit:

- guidance and public review documents outrank registry patterns
- PSG helps with FDA topical technical expectations but does not by itself decide a 505(b)(2) or innovative-drug path
- ClinicalTrials.gov helps with design precedent but does not prove regulatory acceptability
- one FDA public review case should not be turned into a universal rule

## Portability Boundary

The current skill no longer requires author-local raw materials for normal use.

For public-distribution safety, the repo treats China official raw PDFs as an external official-source layer rather than mirroring them by default.

Normal teammate usage should rely on:

- repo-bundled regulatory cards
- repo-bundled case summaries
- official FDA, CDE, NMPA, and ClinicalTrials.gov retrieval when current or citation-ready support is needed

The skill should not fail merely because the original author once used local raw files during drafting.

## Documentation Boundary

Some repository docs were drafted first for local Codex usage and may still contain machine-local absolute paths or file links.

Before GitHub release, check whether any document still needs:

- relative links instead of local absolute links
- a repo-safe description of local-only source files

For a public GitHub release, prefer official links and repo-bundled derivatives over mirrored third-party or China official raw files unless distribution rights are explicitly cleared.

## Recommended Answer Behavior Near A Boundary

When the request sits near a boundary, the answer should:

- explicitly mark uncertainty
- avoid false precision
- say what extra evidence would most improve path confidence
- prefer strategy framing over protocol-like detail
