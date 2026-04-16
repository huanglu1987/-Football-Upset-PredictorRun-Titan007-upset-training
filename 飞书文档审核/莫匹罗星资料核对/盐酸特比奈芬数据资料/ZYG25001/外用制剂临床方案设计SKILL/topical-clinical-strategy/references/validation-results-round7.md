# Validation Results Round 7

## Purpose

This file records the release-prep and business-acceptance findings captured in round 7.

## Prompts Reviewed

Priority review focus:

- Prompt 1: Minimal-input acne oral-to-topical FDA-first case
- Prompt 9: Terbinafine dual-region business-near case
- Prompt 10: Minoxidil optimization dual-region case

## Findings

### Finding 1: Team-facing release materials needed explicit scope and boundary language

Observed risk:

- The skill had become materially stronger, but the handoff documents still focused more on installation than on where the current version should and should not be trusted.

Impact:

- teammates could over-read strategy answers outside the current deep-fit scope

Fix:

- added `references/known-boundaries.md`
- connected the boundary note back into the workflow and usage guide

### Finding 2: Same-target trial-design precedent deserved its own source layer

Observed risk:

- Guidance and FDA public reviews cover regulatory logic well, but they do not always expose current same-target design patterns for duration, comparator choice, endpoint timing, or extension strategy.

Impact:

- answers could miss useful operational precedent, especially for oral-to-topical or class-expansion projects

Fix:

- added `references/clinicaltrials-strategy.md`
- added `ClinicalTrials.gov` as a supportive registry layer in the source map and workflow

### Finding 3: GitHub release preparation needed a concrete checklist, not just a future intention

Observed risk:

- The project already had an installer and trial guide, but there was no explicit pre-release checklist to catch machine-local dependencies or document portability problems.

Impact:

- a later GitHub release could appear ready while still carrying local-only assumptions

Fix:

- added a GitHub release-prep guide under `docs/superpowers/guides/`
- explicitly called out local raw-material paths and local absolute doc links as release checks

## Remaining Gaps

- China-side public trial-registry integration is still not formalized as a separate layer.
- The skill does not yet include a dedicated automated query helper for same-target ClinicalTrials.gov pulls.
- Local raw PDFs and CSVs used during authoring have not been repackaged into repo-safe derivatives for GitHub distribution.
