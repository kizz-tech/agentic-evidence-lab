import unittest

from server import handle


class ServerSmokeTests(unittest.TestCase):
    def test_initialize(self) -> None:
        result = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual("weather", result["result"]["name"])


if __name__ == "__main__":
    unittest.main()
