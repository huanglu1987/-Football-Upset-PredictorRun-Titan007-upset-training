---
name: football-upset-predictor
description: Run the Titan007 football upset workflow in /Users/huanglu/Projects/球探冷门 for historical retraining, future date-range prediction, combined leaderboard review, and draw-upset ranking.
---

# Football Upset Predictor

Use this skill when the user wants to run or update the football cold-upset workflow in `/Users/huanglu/Projects/球探冷门`.

## Predict a date range to Excel

Use the convenience entrypoint:

```bash
cd /Users/huanglu/Projects/球探冷门
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-excel --start-date YYYY-MM-DD --end-date YYYY-MM-DD --top-n 20
```

Defaults:
- main model: `/Users/huanglu/Projects/球探冷门/data/models/titan007_softmax_model.json`
- draw model: `/Users/huanglu/Projects/球探冷门/data/models/titan007_draw_softmax_model.json`
- competitions: Titan007 all competitions by default; pass `--competitions` only when the user wants an explicit subset

When reporting results:
- prioritize the betting recommendation summary rather than raw probability tables
- only keep rows where:
  - `bet_confidence ∈ {强, 中, 弱}`
  - `bet_direction != 不投注`
- sort the final betting list by `强 -> 中 -> 弱`, while preserving the existing recommendation order inside each confidence bucket
- the final betting list should only keep these 5 fields:
  - `比赛时间`
  - `对阵`
  - `等级`
  - `建议方向`
  - `原因`
- do not include probability or raw model columns in the final betting list
- still treat `combined_candidate_label` as the model primary direction and `secondary_candidate_label` as the fallback direction when helpful
- if the draw model is present, mention the draw leaderboard only as supporting context, not as the main result

Artifacts land under `/Users/huanglu/Projects/球探冷门/data/interim/titan007/<run_id>/`, including:
- `prediction_report.xlsx`
- `betting_recommendations.csv`
- `betting_recommendations.json`
- `combined_rankings.csv`
- `draw_rankings.csv`
- `all` prediction JSON/CSV artifacts

## Refresh historical windows and retrain both models

Use the same entrypoint:

```bash
cd /Users/huanglu/Projects/球探冷门
PYTHONPATH=src python3 scripts/titan007_skill_entry.py refresh-models --validation-season 2526
```

Current default training behavior:
- merged history rows remain fully retained
- default model training uses the `full_markets` subset
- `1x2_only` rows are kept for analysis and fallback research, but are not the default online model training set

Default history window config:
- `/Users/huanglu/Projects/球探冷门/data/interim/titan007/default_history_windows.json`

Merged training rows are written to:
- `/Users/huanglu/Projects/球探冷门/data/interim/titan007/merged_default_windows/training_rows.csv`

For quick retraining from an already prepared CSV, you can still use:

```bash
cd /Users/huanglu/Projects/球探冷门
PYTHONPATH=src python3 scripts/titan007_skill_entry.py train-models --input-path /absolute/path/to/training_rows.csv --validation-season 2526
```

## Guardrails

- Do not silently swap data sources away from Titan007 unless the user asks.
- If the main model file is missing, tell the user to retrain before predicting.
- If the draw model file is missing, prediction can still run, but say that draw ranking was skipped.
- Prefer summarizing betting recommendations first, then the combined leaderboard, then the draw leaderboard.
- Prefer returning the Excel path plus the filtered top betting recommendations, not only raw CSV paths.
