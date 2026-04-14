from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.backfill_titan007_history import main as backfill_history_main
from scripts.predict_titan007_range import main as predict_range_main
from scripts.train_draw_model import main as train_draw_main
from scripts.train_upset_model import main as train_upset_main
from upset_model.config import TITAN007_INTERIM_DIR, TITAN007_RAW_DIR, normalize_titan007_competition_filters
from upset_model.history_expander import load_history_window_groups, merge_training_row_files
from upset_model.modeling import load_model_artifact

DEFAULT_REFRESH_ROWS_PATH = PROJECT_ROOT / "data" / "interim" / "titan007" / "merged_default_windows" / "training_rows.csv"
DEFAULT_INPUT_PATH = DEFAULT_REFRESH_ROWS_PATH
DEFAULT_MAIN_MODEL_PATH = PROJECT_ROOT / "data" / "models" / "titan007_softmax_model.json"
DEFAULT_DRAW_MODEL_PATH = PROJECT_ROOT / "data" / "models" / "titan007_draw_softmax_model.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data" / "interim" / "training_reports"
DEFAULT_WINDOW_CONFIG_PATH = PROJECT_ROOT / "data" / "interim" / "titan007" / "default_history_windows.json"
DEFAULT_REFRESH_CACHE_ROOT = TITAN007_INTERIM_DIR / "refresh_cache"
DEFAULT_VENV_PATH = PROJECT_ROOT / ".venv"
DEFAULT_REPO_SKILL_PATH = PROJECT_ROOT / "skills" / "football-upset-predictor" / "SKILL.md"

PREDICTION_RUN_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")
HISTORY_RUN_PATTERN = re.compile(r"^history_\d{8}T\d{6}Z$")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convenience entrypoint for the Titan007 upset workflow.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    predict_parser = subparsers.add_parser(
        "predict-range",
        help="Fetch Titan007 public pages for a date range and score the matches with the active models.",
    )
    predict_parser.add_argument("--start-date", required=True, help="Inclusive start date in YYYY-MM-DD format.")
    predict_parser.add_argument("--end-date", required=True, help="Inclusive end date in YYYY-MM-DD format.")
    predict_parser.add_argument("--top-n", type=int, default=20, help="How many matches to print from each leaderboard.")
    predict_parser.add_argument("--model-path", type=Path, default=DEFAULT_MAIN_MODEL_PATH, help="Main upset model path.")
    predict_parser.add_argument(
        "--draw-model-path",
        type=Path,
        default=DEFAULT_DRAW_MODEL_PATH,
        help="Optional draw-upset model path. If the file does not exist, draw ranking is skipped.",
    )
    predict_parser.add_argument(
        "--competitions",
        nargs="*",
        help="Optional competition-code filter, for example E0 SP1 D1 I1 F1.",
    )

    predict_excel_parser = subparsers.add_parser(
        "predict-excel",
        help="Run the Titan007 prediction flow and export an Excel workbook.",
    )
    predict_excel_parser.add_argument("--start-date", required=True, help="Inclusive start date in YYYY-MM-DD format.")
    predict_excel_parser.add_argument("--end-date", required=True, help="Inclusive end date in YYYY-MM-DD format.")
    predict_excel_parser.add_argument("--top-n", type=int, default=20, help="How many matches to print from each leaderboard.")
    predict_excel_parser.add_argument("--model-path", type=Path, default=DEFAULT_MAIN_MODEL_PATH, help="Main upset model path.")
    predict_excel_parser.add_argument(
        "--draw-model-path",
        type=Path,
        default=DEFAULT_DRAW_MODEL_PATH,
        help="Optional draw-upset model path. If the file does not exist, draw ranking is skipped.",
    )
    predict_excel_parser.add_argument(
        "--competitions",
        nargs="*",
        help="Optional competition-code filter, for example E0 SP1 D1 I1 F1.",
    )
    predict_excel_parser.add_argument(
        "--output-path",
        type=Path,
        help="Optional output path for the Excel workbook. Defaults to <run_dir>/prediction_report.xlsx.",
    )

    train_parser = subparsers.add_parser(
        "train-models",
        help="Retrain both the main upset model and the draw-upset model from normalized Titan007 rows.",
    )
    train_parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Normalized training rows CSV. Defaults to the merged Titan007 default-window dataset.",
    )
    train_parser.add_argument(
        "--validation-season",
        help="Season key to hold out for validation, for example 2526. Defaults to the latest available season.",
    )
    train_parser.add_argument(
        "--market-profile",
        choices=["all", "full_markets", "1x2_only", "partial_markets"],
        default="full_markets",
        help="Market-completeness cohort used for default model training.",
    )
    train_parser.add_argument("--main-model-path", type=Path, default=DEFAULT_MAIN_MODEL_PATH, help="Output path for the main upset model.")
    train_parser.add_argument("--draw-model-path", type=Path, default=DEFAULT_DRAW_MODEL_PATH, help="Output path for the draw-upset model.")

    refresh_parser = subparsers.add_parser(
        "refresh-models",
        help="Backfill the default Titan007 history windows, merge rows, and retrain both models.",
    )
    refresh_parser.add_argument(
        "--window-config-path",
        type=Path,
        default=DEFAULT_WINDOW_CONFIG_PATH,
        help="JSON file describing the default Titan007 history windows.",
    )
    refresh_parser.add_argument(
        "--merged-output-path",
        type=Path,
        default=DEFAULT_REFRESH_ROWS_PATH,
        help="Where to write the merged normalized training rows CSV.",
    )
    refresh_parser.add_argument(
        "--validation-season",
        help="Season key to hold out for validation, for example 2526. Defaults to the latest available season.",
    )
    refresh_parser.add_argument(
        "--market-profile",
        choices=["all", "full_markets", "1x2_only", "partial_markets"],
        default="full_markets",
        help="Market-completeness cohort used for default model training after refresh.",
    )
    refresh_parser.add_argument(
        "--skip-side-markets",
        action="store_true",
        help="Use 1X2-only historical backfill for faster sample expansion.",
    )
    refresh_parser.add_argument("--main-model-path", type=Path, default=DEFAULT_MAIN_MODEL_PATH, help="Output path for the main upset model.")
    refresh_parser.add_argument("--draw-model-path", type=Path, default=DEFAULT_DRAW_MODEL_PATH, help="Output path for the draw-upset model.")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Prepare a fresh machine: create data directories, install Python dependencies, and install the Codex skill.",
    )
    bootstrap_parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to create the virtual environment and install dependencies.",
    )
    bootstrap_parser.add_argument(
        "--venv-path",
        type=Path,
        default=DEFAULT_VENV_PATH,
        help="Virtual environment path. Defaults to <repo>/.venv.",
    )
    bootstrap_parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Install dependencies into the selected Python directly instead of creating a virtual environment.",
    )
    bootstrap_parser.add_argument(
        "--skip-install-skill",
        action="store_true",
        help="Skip copying the repository skill into the local Codex skills directory.",
    )
    bootstrap_parser.add_argument(
        "--codex-home",
        type=Path,
        help="Optional CODEX_HOME override. Defaults to $CODEX_HOME or ~/.codex.",
    )
    bootstrap_parser.add_argument(
        "--run-refresh-models",
        action="store_true",
        help="After environment setup, immediately run refresh-models for first-time model initialization.",
    )
    bootstrap_parser.add_argument(
        "--validation-season",
        default="2526",
        help="Validation season used when --run-refresh-models is enabled. Defaults to 2526.",
    )
    bootstrap_parser.add_argument(
        "--market-profile",
        choices=["all", "full_markets", "1x2_only", "partial_markets"],
        default="full_markets",
        help="Training cohort used when --run-refresh-models is enabled.",
    )
    bootstrap_parser.add_argument(
        "--skip-side-markets",
        action="store_true",
        help="Use 1X2-only historical backfill when --run-refresh-models is enabled.",
    )

    return parser.parse_args(argv)


def _list_matching_run_dirs(pattern: re.Pattern[str]) -> set[Path]:
    if not TITAN007_INTERIM_DIR.exists():
        return set()
    return {
        path
        for path in TITAN007_INTERIM_DIR.iterdir()
        if path.is_dir() and pattern.match(path.name)
    }


def _select_new_run_dir(before: set[Path], after: set[Path]) -> Path | None:
    created = sorted(after - before)
    if created:
        return created[-1]
    if after:
        return sorted(after)[-1]
    return None


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_codex_home(codex_home: Path | None = None) -> Path:
    if codex_home is not None:
        return codex_home.expanduser().resolve()
    env_value = os.environ.get("CODEX_HOME")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def codex_skill_install_path(codex_home: Path | None = None) -> Path:
    return resolve_codex_home(codex_home) / "skills" / "football-upset-predictor" / "SKILL.md"


def resolve_venv_python_path(venv_path: Path) -> Path:
    return venv_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _run_command(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def load_project_dependencies(pyproject_path: Path | None = None) -> list[str]:
    target = pyproject_path or (PROJECT_ROOT / "pyproject.toml")
    payload = tomllib.loads(target.read_text(encoding="utf-8"))
    project = payload.get("project", {})
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        return []
    return [str(item) for item in dependencies]


def _group_cache_paths(label: str) -> tuple[Path, Path, Path, Path]:
    interim_dir = DEFAULT_REFRESH_CACHE_ROOT / label
    raw_dir = TITAN007_RAW_DIR / "refresh_cache" / label
    output_path = interim_dir / "training_rows.csv"
    summary_path = interim_dir / "run_summary.json"
    return raw_dir, interim_dir, output_path, summary_path


def _cache_summary_is_reusable(
    *,
    summary_path: Path,
    output_path: Path,
    competition_filter_mode: str,
    requested_competitions: list[str],
) -> bool:
    if not output_path.exists():
        return False
    if not summary_path.exists():
        return True
    try:
        payload = _load_json(summary_path)
    except Exception:
        return False
    cached_requested = sorted(str(item) for item in payload.get("requested_competitions", payload.get("selected_competitions", [])))
    cached_mode = str(payload.get("competition_filter_mode", "explicit" if cached_requested else "all"))
    if cached_mode != competition_filter_mode:
        return False
    if cached_requested != sorted(requested_competitions):
        return False
    return int(payload.get("failure_count", 0)) == 0 and int(payload.get("training_row_count", 0)) > 0


def _cached_date_ranges(summary_path: Path) -> list[str]:
    if not summary_path.exists():
        return []
    try:
        payload = _load_json(summary_path)
    except Exception:
        return []
    return [str(item) for item in payload.get("date_ranges", [])]


def _build_predict_forwarded_args(args: argparse.Namespace) -> list[str]:
    forwarded_args = [
        "--start-date",
        args.start_date,
        "--end-date",
        args.end_date,
        "--top-n",
        str(args.top_n),
        "--model-path",
        str(args.model_path),
    ]
    if args.draw_model_path.exists():
        forwarded_args.extend(["--draw-model-path", str(args.draw_model_path)])
    else:
        print(f"Draw model not found, continuing without draw ranking: {args.draw_model_path}")
    if args.competitions:
        forwarded_args.extend(["--competitions", *args.competitions])
    return forwarded_args


def _predict_range(args: argparse.Namespace) -> int:
    if not args.model_path.exists():
        print(f"Main upset model not found: {args.model_path}")
        print("Run `train-models` or `refresh-models` first, or pass --model-path explicitly.")
        return 1
    return predict_range_main(_build_predict_forwarded_args(args))


def _predict_excel(args: argparse.Namespace) -> int:
    if not args.model_path.exists():
        print(f"Main upset model not found: {args.model_path}")
        print("Run `train-models` or `refresh-models` first, or pass --model-path explicitly.")
        return 1

    before_runs = _list_matching_run_dirs(PREDICTION_RUN_PATTERN)
    exit_code = predict_range_main(_build_predict_forwarded_args(args))
    if exit_code != 0:
        return exit_code

    after_runs = _list_matching_run_dirs(PREDICTION_RUN_PATTERN)
    run_dir = _select_new_run_dir(before_runs, after_runs)
    if run_dir is None:
        print("Prediction finished, but the run directory could not be located.")
        return 1

    from upset_model.excel_report import build_prediction_excel_report_from_run_dir

    main_artifact = load_model_artifact(args.model_path)
    draw_artifact = load_model_artifact(args.draw_model_path) if args.draw_model_path.exists() else None
    excel_path = build_prediction_excel_report_from_run_dir(
        run_dir=run_dir,
        main_artifact=main_artifact,
        draw_artifact=draw_artifact,
        output_path=args.output_path,
    )
    summary_path = run_dir / "run_summary.json"
    if summary_path.exists():
        summary_payload = _load_json(summary_path)
        summary_payload["excel_report_path"] = str(excel_path)
        _write_json(summary_path, summary_payload)

    print(f"Excel report saved to {excel_path}")
    return 0


def _train_models(args: argparse.Namespace) -> int:
    if not args.input_path.exists():
        print(f"Training rows CSV not found: {args.input_path}")
        print("Run the Titan007 history backfill first, or pass --input-path explicitly.")
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    main_report_path = DEFAULT_REPORT_DIR / f"titan007_training_report_{run_id}.json"
    draw_report_path = DEFAULT_REPORT_DIR / f"titan007_draw_training_report_{run_id}.json"

    main_args = [
        "--input-path",
        str(args.input_path),
        "--class-weight-strategy",
        "none",
        "--epochs",
        "120",
        "--learning-rate",
        "0.04",
        "--l2",
        "0.0005",
        "--accuracy-floor",
        "0.60",
        "--min-predicted-upsets",
        "10",
        "--model-path",
        str(args.main_model_path),
        "--report-path",
        str(main_report_path),
        "--market-profile",
        args.market_profile,
    ]
    draw_args = [
        "--input-path",
        str(args.input_path),
        "--class-weight-strategy",
        "sqrt_balanced",
        "--epochs",
        "120",
        "--learning-rate",
        "0.06",
        "--l2",
        "0.0005",
        "--accuracy-floor",
        "0.60",
        "--min-predicted-draws",
        "10",
        "--model-path",
        str(args.draw_model_path),
        "--report-path",
        str(draw_report_path),
        "--market-profile",
        args.market_profile,
    ]
    if args.validation_season:
        main_args.extend(["--validation-season", args.validation_season])
        draw_args.extend(["--validation-season", args.validation_season])

    main_exit = train_upset_main(main_args)
    if main_exit != 0:
        return main_exit
    return train_draw_main(draw_args)


def _refresh_models(args: argparse.Namespace) -> int:
    if not args.window_config_path.exists():
        print(f"Window config not found: {args.window_config_path}")
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    refresh_run_dir = TITAN007_INTERIM_DIR / f"model_refresh_{run_id}"
    refresh_run_dir.mkdir(parents=True, exist_ok=True)

    window_groups = load_history_window_groups(args.window_config_path)
    successful_paths: list[Path] = []
    group_results: list[dict[str, object]] = []

    for group in window_groups:
        raw_cache_dir, interim_cache_dir, output_path, summary_path = _group_cache_paths(group.label)
        competitions = group.competitions
        requested_competitions = sorted(normalize_titan007_competition_filters(competitions))
        competition_filter_mode = "explicit" if requested_competitions else "all"
        cached_ranges = _cached_date_ranges(summary_path)
        requested_ranges = [str(item) for item in group.date_ranges]
        missing_ranges = [item for item in requested_ranges if item not in cached_ranges]
        if (
            not missing_ranges
            and _cache_summary_is_reusable(
                summary_path=summary_path,
                output_path=output_path,
                competition_filter_mode=competition_filter_mode,
                requested_competitions=requested_competitions,
            )
        ):
            history_summary = _load_json(summary_path) if summary_path.exists() else {
                "training_row_count": 0,
                "failure_count": 0,
            }
            status = "cached"
            history_run_dir = interim_cache_dir
        else:
            incremental_output_path = interim_cache_dir / f"incremental_{run_id}.csv"
            incremental_interim_dir = interim_cache_dir / f"incremental_{run_id}"
            forwarded_args: list[str] = []
            for date_range in (missing_ranges or requested_ranges):
                forwarded_args.extend(["--date-range", date_range])
            if competitions:
                forwarded_args.extend(["--competitions", *competitions])
            forwarded_args.extend(
                [
                    "--output-path",
                    str(incremental_output_path),
                    "--raw-dir",
                    str(raw_cache_dir),
                    "--interim-dir",
                    str(incremental_interim_dir),
                ]
            )
            if args.skip_side_markets:
                forwarded_args.append("--skip-side-markets")
            exit_code = backfill_history_main(forwarded_args)
            incremental_summary_path = incremental_interim_dir / "run_summary.json"
            incremental_summary = _load_json(incremental_summary_path) if incremental_summary_path.exists() else {}
            if exit_code == 0 and incremental_output_path.exists():
                merge_inputs = [incremental_output_path]
                if output_path.exists():
                    merge_inputs.insert(0, output_path)
                merged_output_path, merged_count = merge_training_row_files(merge_inputs, output_path=output_path)
                existing_summary = _load_json(summary_path) if summary_path.exists() else {}
                merged_selected_competitions = sorted(
                    {
                        *[str(item) for item in existing_summary.get("selected_competitions", [])],
                        *[str(item) for item in incremental_summary.get("selected_competitions", [])],
                    }
                )
                history_summary = {
                    "date_ranges": requested_ranges,
                    "competition_filter_mode": competition_filter_mode,
                    "requested_competitions": requested_competitions,
                    "selected_competitions": merged_selected_competitions,
                    "training_row_count": merged_count,
                    "failure_count": incremental_summary.get("failure_count", 0),
                    "training_rows_path": str(merged_output_path),
                    "raw_dir": str(raw_cache_dir),
                    "interim_dir": str(interim_cache_dir),
                }
                _write_json(summary_path, history_summary)
                history_run_dir = interim_cache_dir
                status = "updated" if output_path.exists() and cached_ranges else "ok"
            else:
                history_run_dir = incremental_interim_dir
                history_summary = incremental_summary
                status = "failed"
        if status in {"ok", "updated"}:
            successful_paths.append(output_path)
        elif status == "cached":
            successful_paths.append(output_path)
        group_results.append(
            {
                "label": group.label,
                "date_ranges": group.date_ranges,
                "competitions": competitions,
                "note": group.note,
                "competition_filter_mode": competition_filter_mode,
                "status": status,
                "output_path": str(output_path),
                "history_run_dir": str(history_run_dir) if history_run_dir else "",
                "training_row_count": history_summary.get("training_row_count", 0),
                "failure_count": history_summary.get("failure_count", 0),
            }
        )

    if not successful_paths:
        print("No history windows were successfully backfilled, aborting model refresh.")
        return 1

    merged_output_path, merged_row_count = merge_training_row_files(successful_paths, output_path=args.merged_output_path)
    training_namespace = argparse.Namespace(
        input_path=merged_output_path,
        validation_season=args.validation_season,
        market_profile=args.market_profile,
        main_model_path=args.main_model_path,
        draw_model_path=args.draw_model_path,
    )
    train_exit = _train_models(training_namespace)
    if train_exit != 0:
        return train_exit

    main_report_candidates = sorted(DEFAULT_REPORT_DIR.glob("titan007_training_report_*.json"))
    draw_report_candidates = sorted(DEFAULT_REPORT_DIR.glob("titan007_draw_training_report_*.json"))
    main_report_path = main_report_candidates[-1] if main_report_candidates else None
    draw_report_path = draw_report_candidates[-1] if draw_report_candidates else None
    summary_payload = {
        "run_id": run_id,
        "window_config_path": str(args.window_config_path),
        "skip_side_markets": args.skip_side_markets,
        "training_market_profile": args.market_profile,
        "group_count": len(window_groups),
        "successful_group_count": sum(1 for item in group_results if item["status"] in {"ok", "updated", "cached"}),
        "failed_group_count": sum(1 for item in group_results if item["status"] not in {"ok", "updated", "cached"}),
        "merged_output_path": str(merged_output_path),
        "merged_row_count": merged_row_count,
        "main_model_path": str(args.main_model_path),
        "draw_model_path": str(args.draw_model_path),
        "main_report_path": str(main_report_path) if main_report_path else "",
        "draw_report_path": str(draw_report_path) if draw_report_path else "",
        "groups": group_results,
    }
    if main_report_path and main_report_path.exists():
        summary_payload["main_metrics"] = _load_json(main_report_path)
    if draw_report_path and draw_report_path.exists():
        summary_payload["draw_metrics"] = _load_json(draw_report_path)

    summary_path = refresh_run_dir / "refresh_summary.json"
    _write_json(summary_path, summary_payload)
    print(f"Model refresh summary saved to {summary_path}")
    print(f"Merged training rows saved to {merged_output_path}")
    return 0


def _bootstrap_refresh_namespace(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        window_config_path=DEFAULT_WINDOW_CONFIG_PATH,
        merged_output_path=DEFAULT_REFRESH_ROWS_PATH,
        validation_season=args.validation_season,
        market_profile=args.market_profile,
        skip_side_markets=args.skip_side_markets,
        main_model_path=DEFAULT_MAIN_MODEL_PATH,
        draw_model_path=DEFAULT_DRAW_MODEL_PATH,
    )


def _bootstrap(args: argparse.Namespace) -> int:
    required_dirs = [
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data" / "raw",
        PROJECT_ROOT / "data" / "interim",
        PROJECT_ROOT / "data" / "features",
        PROJECT_ROOT / "data" / "models",
    ]
    for path in required_dirs:
        path.mkdir(parents=True, exist_ok=True)

    if args.skip_venv:
        python_cmd = [args.python]
    else:
        args.venv_path.mkdir(parents=True, exist_ok=True)
        venv_python = resolve_venv_python_path(args.venv_path)
        if not venv_python.exists():
            _run_command([args.python, "-m", "venv", str(args.venv_path)], cwd=PROJECT_ROOT)
        python_cmd = [str(resolve_venv_python_path(args.venv_path))]

    _run_command([*python_cmd, "-m", "pip", "install", "--upgrade", "pip"], cwd=PROJECT_ROOT)
    dependencies = load_project_dependencies()
    if dependencies:
        _run_command([*python_cmd, "-m", "pip", "install", *dependencies], cwd=PROJECT_ROOT)

    if not args.skip_install_skill:
        install_path = codex_skill_install_path(args.codex_home)
        install_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEFAULT_REPO_SKILL_PATH, install_path)
        print(f"Codex skill installed to {install_path}")

    if args.skip_venv:
        install_python = args.python
    else:
        install_python = str(resolve_venv_python_path(args.venv_path))

    if args.run_refresh_models:
        print("Running refresh-models as requested...")
        refresh_exit = _refresh_models(_bootstrap_refresh_namespace(args))
        if refresh_exit != 0:
            return refresh_exit

    print("Bootstrap completed.")
    if not args.skip_venv:
        activation_hint = args.venv_path / ("Scripts/activate" if os.name == "nt" else "bin/activate")
        print(f"Activate the virtual environment with: source {activation_hint}")
    if args.run_refresh_models:
        print("Models initialized during bootstrap.")
    else:
        print(
            "First-time model setup: "
            f"PYTHONPATH=src {install_python} scripts/titan007_skill_entry.py refresh-models --validation-season {args.validation_season}"
        )
    print(
        "Prediction example: "
        f"PYTHONPATH=src {install_python} scripts/titan007_skill_entry.py predict-excel --start-date YYYY-MM-DD --end-date YYYY-MM-DD --top-n 20"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "bootstrap":
        return _bootstrap(args)
    if args.command == "predict-range":
        return _predict_range(args)
    if args.command == "predict-excel":
        return _predict_excel(args)
    if args.command == "train-models":
        return _train_models(args)
    if args.command == "refresh-models":
        return _refresh_models(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
