import sys
import unittest
from pathlib import Path


WORKSPACE = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(WORKSPACE))

from slug import normalize_slug


class AcceptanceTests(unittest.TestCase):
    def test_collapses_mixed_unicode_whitespace(self) -> None:
        self.assertEqual("alpha-beta", normalize_slug(" Alpha\t \nBeta "))

    def test_whitespace_only_is_empty(self) -> None:
        self.assertEqual("", normalize_slug(" \t\n "))


if __name__ == "__main__":
    unittest.main()

