# Validation Results Round 4

## Purpose

This file records the main issues found during the first manual validation pass and the fixes made in round 4.

## Prompts Reviewed

Priority review focus:

- Prompt 1: Minimal-input acne case
- Prompt 4: Superficial fungal short-course case
- Prompt 5: AGA finasteride-risk case
- Prompt 8: Dual-region uncertain path case

## Findings

### Finding 1: Single-region outputs risked over-structuring cross-region comparison

Observed risk:

- The output template could encourage a full `CDE vs FDA` block even when the user asked for only one region.

Impact:

- answers could become noisy and less practical

Fix:

- added `references/output-self-check.md`
- clarified that cross-region comparison should be real and conditional, not forced

### Finding 2: Sparse-input prompts needed a more explicit first-pass mode

Observed risk:

- The skill already tolerated missing inputs, but the answer structure did not explicitly mark “this is only a first-pass strategy judgment.”

Impact:

- sparse-input answers might sound more settled than they really are

Fix:

- added explicit first-pass mode rules in `references/output-self-check.md`
- required key assumptions and highest-impact evidence gaps to be named

### Finding 3: Team testing needed a final delivery checklist

Observed risk:

- Even with good references, the final answer could still omit a recommended path, omit evidence labels, or drift into protocol-writing style

Impact:

- inconsistent team usage

Fix:

- added `references/output-self-check.md`
- connected self-check into the main workflow

### Finding 4: Validation artifacts were present, but validation outcomes were not recorded

Observed risk:

- The skill had test prompts but no retained record of what was learned from running them

Impact:

- future iterations would lose context and repeat the same mistakes

Fix:

- added this file as a lightweight running validation log

## Remaining Gaps

- More detailed PSG-to-active mapping is still needed for a later round.
- More negative examples are still needed for AGA and superficial fungal edge cases.
- A future round should capture example outputs from real product scenarios, not only prompts.
