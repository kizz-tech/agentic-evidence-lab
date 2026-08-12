import unittest

from discount import price_after_discount


class DiscountSmokeTests(unittest.TestCase):
    def test_existing_price(self) -> None:
        self.assertEqual(80, price_after_discount(100, 20))


if __name__ == "__main__":
    unittest.main()
