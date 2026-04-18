---
name: football-upset-predictor
description: Run the Titan007 football upset workflow from the current cloned repository for historical retraining, future date-range prediction, combined leaderboard review, and draw-upset ranking.
---

# Football Upset Predictor

Use this skill when the user wants to run or update the football cold-upset workflow from the currently opened repository.

Repository bootstrap on a fresh machine:

```bash
git clone <your-repo-url>
cd <repo-dir>
bash scripts/bootstrap_repo.sh
```

The repository now ships with the default Titan007 models under `<repo>/data/models/`, so a fresh clone can run `predict-range` / `predict-excel` immediately without retraining first.

If the machine is brand new and you want bootstrap to immediately build the first local models, run:

```bash
bash scripts/bootstrap_repo.sh --run-refresh-models
```

## Predict a date or datetime range to Excel

Use the convenience entrypoint:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-excel --start-date YYYY-MM-DD --end-date YYYY-MM-DD --top-n 20
```

For minute-level windows, use:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-excel --start-datetime "YYYY-MM-DD HH:MM" --end-datetime "YYYY-MM-DD HH:MM" --top-n 20
```

Defaults:
- main model: `<repo>/data/models/titan007_softmax_model.json`
- draw model: `<repo>/data/models/titan007_draw_softmax_model.json`
- fresh clones can use these bundled default models immediately; `refresh-models` is only needed when the user wants to regenerate newer local models
- competitions: by default follow the active main model training domain; if the model metadata says `all`, predict all Titan007 competitions, otherwise reuse the model's explicit training competitions; if metadata is missing, fall back to `E0 SP1 D1 I1 F1`
- fetch mode: default prediction keeps full markets (1X2 + Asian + over/under); use `--skip-side-markets` only for fast pre-screening when the user explicitly accepts reduced market context

When reporting results:
- prioritize the betting recommendation summary rather than raw probability tables
- the final betting list should only keep rows where:
  - `bet_recommendation == 建议投注`
  - in the current code path, this means `bet_confidence ∈ {强, 中}` and `bet_direction != 不投注`
- if there are no actionable betting recommendations, say so clearly and then fall back to the combined leaderboard plus draw leaderboard context
- sort the final betting list by `强 -> 中`, while preserving the existing recommendation order inside each confidence bucket
- the final betting list should only keep these 5 fields:
  - `比赛时间`
  - `对阵`
  - `等级`
  - `建议方向`
  - `原因`
- do not include probability or raw model columns in the final betting list
- treat `弱` / `谨慎关注` as watchlist-only context from the workbook or JSON, not as the primary betting list
- still treat `combined_candidate_label` as the model primary direction and `secondary_candidate_label` as the fallback direction when helpful
- if the draw model is present, mention the draw leaderboard only as supporting context, not as the main result

Artifacts land under `<repo>/data/interim/titan007/<run_id>/`, including:
- `prediction_report.xlsx`
- `betting_recommendations.csv`
- `betting_recommendations.json`
- `combined_rankings.csv`
- `draw_rankings.csv`
- `all` prediction JSON/CSV artifacts

## Refresh historical windows and retrain both models

Use the same entrypoint:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
PYTHONPATH=src python3 scripts/titan007_skill_entry.py refresh-models --validation-season 2526
```

Current default training behavior:
- merged history rows remain fully retained
- default model training uses the `full_markets` subset
- `train-models` / `refresh-models` auto-calibrate the betting policy after training and persist it into the main model artifact
- `train-models` / `refresh-models` also persist the training competition scope into the main model artifact, so later prediction defaults can follow the same domain automatically
- `1x2_only` rows are kept for analysis and fallback research, but are not the default online model training set

Default history window config:
- `<repo>/data/interim/titan007/default_history_windows.json`

Merged training rows are written to:
- `<repo>/data/interim/titan007/merged_default_windows/training_rows.csv`

For quick retraining from an already prepared CSV, you can still use:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
PYTHONPATH=src python3 scripts/titan007_skill_entry.py train-models --input-path /absolute/path/to/training_rows.csv --validation-season 2526
```

## Guardrails

- Do not silently swap data sources away from Titan007 unless the user asks.
- Do not assume "all competitions" unless the active model training domain is actually `all` or the user explicitly passes `--competitions`.
- If the bundled main model file is missing, tell the user to run `refresh-models` before predicting.
- If the draw model file is missing, prediction can still run, but say that draw ranking was skipped.
- Prefer summarizing betting recommendations first, then the combined leaderboard, then the draw leaderboard.
- Prefer returning the Excel path plus the filtered top betting recommendations, not only raw CSV paths.
