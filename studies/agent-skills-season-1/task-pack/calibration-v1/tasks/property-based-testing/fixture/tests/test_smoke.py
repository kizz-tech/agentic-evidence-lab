import unittest

from codec import decode, encode


class CodecSmokeTests(unittest.TestCase):
    def test_ascii_round_trip(self) -> None:
        self.assertEqual("agent", decode(encode("agent")))


if __name__ == "__main__":
    unittest.main()
