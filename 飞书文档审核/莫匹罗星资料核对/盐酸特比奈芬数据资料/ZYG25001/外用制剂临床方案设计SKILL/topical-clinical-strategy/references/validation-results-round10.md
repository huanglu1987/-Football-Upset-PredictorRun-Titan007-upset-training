# Validation Results Round 10

## Purpose

This file records a public-friendly real-run validation pass using three representative scenarios:

- one improved-new-drug scenario
- one innovative-drug scenario
- one newly added indication scenario

## Scenarios Reviewed

### Scenario 1: Improved New Drug

- case used: `worked-examples/minoxidil-optimization-dual-region.md`
- goal: verify that the current skill still handles a relatively strong-precedent optimization program cleanly

### Scenario 2: Innovative Drug

- case used: `worked-examples/ad-innovative-dual-region.md`
- goal: verify that the new innovative-topical rule layer produces a real proof-of-concept-oriented answer rather than falling back to improved-drug bridge language

### Scenario 3: Newly Added Indication

- case used: `worked-examples/seborrheic-dermatitis-foam-dual-region.md`
- goal: verify that a new indication module can drive disease-specific strategy rather than inheriting fungal or generic dermatitis logic

## Main Findings

### Finding 1: Improved-new-drug output remained structurally stable

Observed result:

- The minoxidil optimization scenario still produced a clean dual-path answer.
- The current skill correctly kept AGA as a long-horizon program and did not over-compress the observation window.

Conclusion:

- no structural output fix was required for this scenario

### Finding 2: Innovative-drug answers needed a sharper proof-of-concept check

Observed result:

- The new innovative-topical layer improved the answer materially, but the final output quality still depends on whether the responder explicitly states that the early package is solving a proof-of-concept problem rather than a bridge problem.

Risk:

- without that explicit distinction, innovative-topical outputs can still sound too similar to improved-drug outputs

Fix:

- strengthened `references/output-self-check.md` with an innovative-program check
- added the AD innovative worked example to anchor answer style

### Finding 3: Newly added chronic relapsing indications needed a clearer claim-intent check

Observed result:

- The seborrheic dermatitis module behaved well, but the answer became much clearer once it explicitly separated acute control from maintenance or relapse-control ambition.

Risk:

- without that distinction, output can drift into an over-broad development claim

Fix:

- strengthened `references/output-self-check.md` with a chronic-relapsing claim-intent check
- added the seborrheic dermatitis worked example

## Residual Gaps

- The new AD and seborrheic dermatitis modules now have worked examples, but their precedent depth is still thinner than acne or AGA optimization.
- A future round should add at least one psoriasis worked example or validation case.
- If the team later wants more innovation-heavy runs, at least one real innovative topical psoriasis or AD scenario should be tested with richer PK assumptions.
