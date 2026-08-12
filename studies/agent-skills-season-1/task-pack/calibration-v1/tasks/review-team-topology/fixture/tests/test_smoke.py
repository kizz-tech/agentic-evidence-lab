import unittest
from pathlib import Path


class ReviewFixtureSmokeTests(unittest.TestCase):
    def test_diff_is_present(self) -> None:
        payload = Path("review_target.diff").read_text(encoding="utf-8")
        self.assertIn("select id", payload)
        self.assertIn("lock.acquire", payload)


if __name__ == "__main__":
    unittest.main()
