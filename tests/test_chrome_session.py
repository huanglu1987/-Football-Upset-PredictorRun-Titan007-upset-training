import unittest
from pathlib import Path

from upset_model.collectors.chrome_session import default_capture_path, parse_tab_listing, slugify_url


class ChromeSessionTests(unittest.TestCase):
    def test_parse_tab_listing(self) -> None:
        raw = (
            "window=1,tab=1,active=2 | https://www.win007.com/ | 首页, "
            "window=1,tab=2,active=2 | view-source:https://www.win007.com/ | 源码"
        )
        tabs = parse_tab_listing(raw)
        self.assertEqual(len(tabs), 2)
        self.assertEqual(tabs[0].url, "https://www.win007.com/")
        self.assertEqual(tabs[1].tab_index, 2)
        self.assertEqual(tabs[1].active_tab_index, 2)

    def test_slugify_url_is_filesystem_safe(self) -> None:
        slug = slugify_url("https://www.win007.com/path?a=1&b=2")
        self.assertNotIn("/", slug)
        self.assertIn("_3A", slug)

    def test_default_capture_path_uses_html_suffix(self) -> None:
        path = default_capture_path("https://www.win007.com/")
        self.assertIsInstance(path, Path)
        self.assertEqual(path.suffix, ".html")


if __name__ == "__main__":
    unittest.main()
