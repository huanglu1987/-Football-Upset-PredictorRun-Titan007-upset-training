# Output Self-Check

## Purpose

Use this file immediately before answering. It is the final delivery checklist for real-user outputs.

## Must-Have Checks

### 1. Region fit

Check:

- If the user asked for US only, do not force a full CDE vs FDA comparison section.
- If the user asked for China only, do not force a full FDA comparison section.
- If both regions matter, include a real comparison instead of a token paragraph.

### 2. Path framing

Check:

- Did the answer clearly state the current path judgment: innovative, improved new drug, or uncertain?
- If uncertain, did the answer explain what evidence would settle the path judgment?

### 3. Conservative vs aggressive routes

Check:

- Did the answer give both paths unless the user explicitly asked for one only?
- Did it explain the one assumption that most strongly separates the two paths?
- Did it clearly say which path is recommended now?

### 4. Evidence labeling

Check:

- Are key recommendations labeled by evidence type?
- Is any single FDA case being overstated as a rule?
- If PSG influenced the answer, did the answer explain that PSG is supportive rather than controlling?
- If ClinicalTrials.gov influenced the answer, did the answer describe it as design precedent rather than regulatory requirement?

### 5. Indication fit

Check:

- Did the answer actually use the relevant indication logic?
- Are the endpoints and timing windows specific to the disease context?

### 6. Uncertainty handling

Check:

- If inputs are sparse, did the answer switch into a first-pass strategy mode?
- Did it clearly mark the highest-impact missing evidence?
- Did it avoid false precision on study count, sample size, or waiver certainty?

## First-Pass Strategy Mode

Use first-pass mode when:

- the user provides only minimal inputs
- path classification is still uncertain
- no human PK or max-use PK exists
- dose or strength rationale is weak

In first-pass mode, the answer should explicitly include:

- `当前判断级别：第一轮策略判断`
- `关键假设`
- `最影响路径变化的 1-3 个缺口`

## Delivery Standard

The answer is not ready if any of the following is true:

- no recommended path is named
- no major missing evidence is named
- no evidence type is attached to the main recommendations
- the answer reads like a protocol synopsis instead of a strategy memo
