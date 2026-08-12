import unittest

from app import render_page


class AppSmokeTests(unittest.TestCase):
    def test_page_contains_form(self) -> None:
        self.assertIn('id="message-form"', render_page())


if __name__ == "__main__":
    unittest.main()
