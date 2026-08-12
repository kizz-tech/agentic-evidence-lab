import unittest

from slug import normalize_slug


class NormalizeSlugTests(unittest.TestCase):
    def test_lowercases_and_replaces_a_space(self) -> None:
        self.assertEqual("hello-world", normalize_slug("Hello World"))

    def test_trims_outer_spaces(self) -> None:
        self.assertEqual("hello", normalize_slug("  Hello  "))


if __name__ == "__main__":
    unittest.main()

