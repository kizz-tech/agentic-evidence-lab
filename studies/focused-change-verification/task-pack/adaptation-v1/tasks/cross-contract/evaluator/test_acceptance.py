import sys
import unittest
from pathlib import Path


WORKSPACE = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(WORKSPACE))

from formatter import format_user
from welcome import welcome, welcome_formal


class AcceptanceTests(unittest.TestCase):
    def test_family_order(self) -> None:
        self.assertEqual("Lovelace, Ada", format_user("Ada", "Lovelace", order="family"))

    def test_default_remains_compatible(self) -> None:
        self.assertEqual("Ada Lovelace", format_user("Ada", "Lovelace"))

    def test_invalid_order_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            format_user("Ada", "Lovelace", order="unknown")

    def test_direct_consumer_uses_family_order(self) -> None:
        self.assertEqual("Welcome, Lovelace, Ada", welcome_formal("Ada", "Lovelace"))

    def test_existing_consumer_remains_compatible(self) -> None:
        self.assertEqual("Welcome, Ada Lovelace", welcome("Ada", "Lovelace"))


if __name__ == "__main__":
    unittest.main()

