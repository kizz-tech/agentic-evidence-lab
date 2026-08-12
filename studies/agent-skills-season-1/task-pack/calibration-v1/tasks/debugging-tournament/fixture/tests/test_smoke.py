import unittest

from limits import parse_limit


class LimitSmokeTests(unittest.TestCase):
    def test_valid_limit(self) -> None:
        self.assertEqual(10, parse_limit(" 10 "))


if __name__ == "__main__":
    unittest.main()
