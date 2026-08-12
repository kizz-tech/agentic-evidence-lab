import sqlite3
import unittest

from db import create_v1


class VersionOneTests(unittest.TestCase):
    def test_v1_fixture_contains_existing_rows(self) -> None:
        connection = sqlite3.connect(":memory:")
        create_v1(connection)
        self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0])


if __name__ == "__main__":
    unittest.main()

