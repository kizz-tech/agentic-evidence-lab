import unittest
from pathlib import Path


class ReviewFixtureSmokeTests(unittest.TestCase):
    def test_diff_is_present(self) -> None:
        self.assertIn("compare_digest", Path("review_target.diff").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
