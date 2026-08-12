import unittest
from pathlib import Path


class FrontendSmokeTests(unittest.TestCase):
    def test_html_exists(self) -> None:
        self.assertIn("<!doctype html>", Path("index.html").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
