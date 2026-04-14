import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.titan007_skill_entry import (
    _cache_summary_is_reusable,
    _cached_date_ranges,
    codex_skill_install_path,
    load_project_dependencies,
    parse_args,
    resolve_codex_home,
    resolve_venv_python_path,
)


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

    def test_parse_args_bootstrap_defaults_to_repo_venv(self) -> None:
        args = parse_args(["bootstrap"])
        self.assertEqual(args.venv_path, PROJECT_ROOT / ".venv")
        self.assertFalse(args.skip_install_skill)

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


if __name__ == "__main__":
    unittest.main()
