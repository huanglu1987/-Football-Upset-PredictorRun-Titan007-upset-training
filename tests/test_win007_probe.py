import unittest
from pathlib import Path

from upset_model.collectors.win007_probe import ProbeReport, save_report
from upset_model.config import expand_probe_urls


class Win007ProbeTests(unittest.TestCase):
    def test_expand_probe_urls_defaults_to_https_only(self) -> None:
        urls = expand_probe_urls()
        self.assertTrue(urls)
        self.assertTrue(all(url.startswith("https://") for url in urls))

    def test_expand_probe_urls_can_include_http(self) -> None:
        urls = expand_probe_urls(include_http=True)
        self.assertTrue(any(url.startswith("http://") for url in urls))
        self.assertTrue(any(url.startswith("https://") for url in urls))

    def test_save_report_writes_json(self) -> None:
        tmp_dir = Path(self._testMethodName)
        output_path = Path.cwd() / "data" / "interim" / "test_reports" / f"{tmp_dir}.json"
        if output_path.exists():
            output_path.unlink()
        report = ProbeReport(
            created_at_utc="2026-04-13T00:00:00+00:00",
            urls=["https://www.win007.com"],
            results=[],
        )
        path = save_report(report, output_path=output_path)
        self.assertTrue(path.exists())
        self.assertIn('"urls"', path.read_text(encoding="utf-8"))
        path.unlink()
        if not any(output_path.parent.iterdir()):
            output_path.parent.rmdir()


if __name__ == "__main__":
    unittest.main()
