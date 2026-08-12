import unittest

from state import format_state


class StateSmokeTests(unittest.TestCase):
    def test_ready_state_keeps_identifier(self) -> None:
        self.assertEqual("ready:job-7", format_state({"id": "job-7", "state": "ready"}))


if __name__ == "__main__":
    unittest.main()
