import unittest

from formatter import format_user
from welcome import welcome


class ExistingContractTests(unittest.TestCase):
    def test_default_order_is_compatible(self) -> None:
        self.assertEqual("Ada Lovelace", format_user("Ada", "Lovelace"))

    def test_existing_consumer_is_compatible(self) -> None:
        self.assertEqual("Welcome, Ada Lovelace", welcome("Ada", "Lovelace"))


if __name__ == "__main__":
    unittest.main()

