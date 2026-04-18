import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.titan007_skill_entry import (
    _build_predict_forwarded_args,
    _cache_summary_is_reusable,
    _cached_date_ranges,
    _bootstrap_refresh_namespace,
    _train_models,
    codex_skill_install_path,
    load_project_dependencies,
    parse_args,
    resolve_codex_home,
    resolve_venv_python_path,
)
from upset_model.modeling import SoftmaxModelArtifact


class Titan007SkillEntryTests(unittest.TestCase):
    def test_cached_date_ranges_reads_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            summary_path = root / "run_summary.json"
            summary_path.write_text(json.dumps({"date_ranges": ["2024-08-16:2024-08-19"]}), encoding="utf-8")

            values = _cached_date_ranges(summary_path)

        self.assertEqual(values, ["2024-08-16:2024-08-19"])

    def test_cache_summary_is_reusable_when_output_exists_without_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "training_rows.csv"
            output_path.write_text("x", encoding="utf-8")
            reusable = _cache_summary_is_reusable(
                summary_path=root / "missing.json",
                output_path=output_path,
                competition_filter_mode="explicit",
                requested_competitions=["E0", "SP1"],
            )

        self.assertTrue(reusable)

    def test_cache_summary_is_not_reusable_when_failures_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "training_rows.csv"
            output_path.write_text("x", encoding="utf-8")
            summary_path = root / "run_summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "competition_filter_mode": "explicit",
                        "requested_competitions": ["E0", "SP1"],
                        "selected_competitions": ["E0", "SP1"],
                        "training_row_count": 120,
                        "failure_count": 3,
                    }
                ),
                encoding="utf-8",
            )
            reusable = _cache_summary_is_reusable(
                summary_path=summary_path,
                output_path=output_path,
                competition_filter_mode="explicit",
                requested_competitions=["E0", "SP1"],
            )

        self.assertFalse(reusable)

    def test_cache_summary_requires_matching_filter_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            output_path = root / "training_rows.csv"
            output_path.write_text("x", encoding="utf-8")
            summary_path = root / "run_summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "competition_filter_mode": "all",
                        "requested_competitions": [],
                        "selected_competitions": ["E0", "T7_U4E2D_U4E59"],
                        "training_row_count": 120,
                        "failure_count": 0,
                    }
                ),
                encoding="utf-8",
            )

            reusable = _cache_summary_is_reusable(
                summary_path=summary_path,
                output_path=output_path,
                competition_filter_mode="explicit",
                requested_competitions=["E0"],
            )

        self.assertFalse(reusable)

    def test_parse_args_accepts_skip_side_markets_for_refresh(self) -> None:
        args = parse_args(["refresh-models", "--skip-side-markets"])
        self.assertTrue(args.skip_side_markets)

    def test_parse_args_defaults_train_models_to_full_markets(self) -> None:
        args = parse_args(["train-models"])
        self.assertEqual(args.market_profile, "full_markets")

    def test_parse_args_predict_excel_accepts_datetime_window(self) -> None:
        args = parse_args(
            [
                "predict-excel",
                "--start-datetime",
                "2026-04-17 22:00",
                "--end-datetime",
                "2026-04-18 12:00",
            ]
        )
        self.assertEqual(args.start_datetime, "2026-04-17 22:00")
        self.assertEqual(args.end_datetime, "2026-04-18 12:00")
        self.assertIsNone(args.start_date)
        self.assertIsNone(args.end_date)

    def test_parse_args_predict_range_accepts_skip_side_markets(self) -> None:
        args = parse_args(
            [
                "predict-range",
                "--start-date",
                "2026-04-18",
                "--end-date",
                "2026-04-18",
                "--skip-side-markets",
            ]
        )

        self.assertTrue(args.skip_side_markets)

    def test_build_predict_forwarded_args_includes_skip_side_markets(self) -> None:
        args = parse_args(
            [
                "predict-excel",
                "--start-date",
                "2026-04-18",
                "--end-date",
                "2026-04-18",
                "--skip-side-markets",
            ]
        )

        forwarded_args = _build_predict_forwarded_args(args)

        self.assertIn("--skip-side-markets", forwarded_args)

    def test_parse_args_bootstrap_defaults_to_repo_venv(self) -> None:
        args = parse_args(["bootstrap"])
        self.assertEqual(args.venv_path, PROJECT_ROOT / ".venv")
        self.assertFalse(args.skip_install_skill)
        self.assertFalse(args.run_refresh_models)
        self.assertEqual(args.validation_season, "2526")

    def test_parse_args_bootstrap_accepts_refresh_flags(self) -> None:
        args = parse_args(["bootstrap", "--run-refresh-models", "--skip-side-markets", "--validation-season", "2425"])
        self.assertTrue(args.run_refresh_models)
        self.assertTrue(args.skip_side_markets)
        self.assertEqual(args.validation_season, "2425")

    def test_codex_skill_install_path_uses_explicit_codex_home(self) -> None:
        target = codex_skill_install_path(Path("/tmp/codex-home"))
        self.assertEqual(target, Path("/tmp/codex-home").resolve() / "skills" / "football-upset-predictor" / "SKILL.md")

    def test_resolve_codex_home_prefers_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            original = os.environ.get("CODEX_HOME")
            os.environ["CODEX_HOME"] = tmp_dir
            try:
                target = resolve_codex_home()
            finally:
                if original is None:
                    os.environ.pop("CODEX_HOME", None)
                else:
                    os.environ["CODEX_HOME"] = original
        self.assertEqual(target, Path(tmp_dir).resolve())

    def test_resolve_venv_python_path_matches_platform(self) -> None:
        target = resolve_venv_python_path(Path("/tmp/repro-venv"))
        self.assertEqual(target.name, "python" if sys.platform != "win32" else "python.exe")

    def test_load_project_dependencies_reads_pyproject(self) -> None:
        dependencies = load_project_dependencies(PROJECT_ROOT / "pyproject.toml")
        self.assertIn("openpyxl>=3.1,<4", dependencies)

    def test_bootstrap_refresh_namespace_uses_refresh_defaults(self) -> None:
        args = parse_args(["bootstrap", "--run-refresh-models", "--validation-season", "2425"])
        refresh_args = _bootstrap_refresh_namespace(args)
        self.assertEqual(refresh_args.validation_season, "2425")
        self.assertEqual(refresh_args.market_profile, "full_markets")
        self.assertEqual(refresh_args.main_model_path, PROJECT_ROOT / "data" / "models" / "titan007_softmax_model.json")

    def test_train_models_uses_balanced_class_weights_for_main_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "training_rows.csv"
            input_path.write_text("season_key\n2526\n", encoding="utf-8")
            args = parse_args(
                [
                    "train-models",
                    "--input-path",
                    str(input_path),
                    "--market-profile",
                    "all",
                    "--main-model-path",
                    str(root / "main.json"),
                    "--draw-model-path",
                    str(root / "draw.json"),
                ]
            )
            calibrated_artifact = SoftmaxModelArtifact(
                created_at_utc="2026-04-18T00:00:00+00:00",
                labels=["home_upset_win", "away_upset_win", "non_upset"],
                feature_names=["feature_a"],
                feature_means=[0.0],
                feature_stds=[1.0],
                weights=[[0.0, 0.0] for _ in range(3)],
                class_weights={"home_upset_win": 1.0, "away_upset_win": 1.0, "non_upset": 1.0},
                validation_season="2526",
                train_size=100,
                validation_size=50,
                metrics={},
                decision_threshold=0.40,
                decision_metrics={},
                betting_policy={"direction_threshold": 0.55},
            )

            with (
                patch("scripts.titan007_skill_entry.DEFAULT_REPORT_DIR", root / "reports"),
                patch("scripts.titan007_skill_entry._load_json", return_value={}),
                patch("scripts.titan007_skill_entry._write_json"),
                patch("scripts.titan007_skill_entry.train_upset_main", return_value=0) as train_upset_main,
                patch("scripts.titan007_skill_entry.train_draw_main", return_value=0),
                patch(
                    "scripts.titan007_skill_entry.load_training_rows",
                    return_value=[
                        SimpleNamespace(competition_code="E0"),
                        SimpleNamespace(competition_code="T7_U4E2D_U4E59"),
                    ],
                ),
                patch("scripts.titan007_skill_entry.split_rows_by_latest_season", return_value=SimpleNamespace(validation_rows=[])),
                patch("scripts.titan007_skill_entry.load_model_artifact", side_effect=[calibrated_artifact, calibrated_artifact]),
                patch("scripts.titan007_skill_entry.calibrate_betting_policy", return_value=(calibrated_artifact, {"direction_threshold": 0.55, "strong_confidence_threshold": 0.1, "medium_confidence_threshold": 0.05})),
                patch("scripts.titan007_skill_entry.save_model_artifact") as save_model_artifact,
            ):
                exit_code = _train_models(args)

        self.assertEqual(exit_code, 0)
        main_args = train_upset_main.call_args.args[0]
        strategy_index = main_args.index("--class-weight-strategy")
        self.assertEqual(main_args[strategy_index + 1], "sqrt_balanced")
        saved_artifact = save_model_artifact.call_args.args[0]
        self.assertEqual(saved_artifact.training_competition_scope, "explicit")
        self.assertEqual(saved_artifact.training_competitions, ["E0", "T7_U4E2D_U4E59"])
        self.assertEqual(saved_artifact.training_market_profile, "all")


if __name__ == "__main__":
    unittest.main()
