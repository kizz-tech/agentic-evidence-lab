import importlib.util
import sqlite3
import sys
import unittest
from pathlib import Path


WORKSPACE = Path(sys.argv.pop(1)).resolve()
sys.path.insert(0, str(WORKSPACE))

from db import create_v1


def load_migration():
    migration_path = WORKSPACE / "migrations" / "002_add_status.py"
    spec = importlib.util.spec_from_file_location("migration_002", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load migration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        create_v1(self.connection)
        self.migration = load_migration()

    def tearDown(self) -> None:
        self.connection.close()

    def test_existing_rows_are_backfilled_and_column_is_required(self) -> None:
        self.migration.upgrade(self.connection)
        rows = self.connection.execute("SELECT status FROM orders ORDER BY id").fetchall()
        self.assertEqual([("pending",), ("pending",)], rows)
        status = next(row for row in self.connection.execute("PRAGMA table_info(orders)") if row[1] == "status")
        self.assertEqual(1, status[3])

    def test_new_rows_receive_default(self) -> None:
        self.migration.upgrade(self.connection)
        self.connection.execute("INSERT INTO orders (total) VALUES (300)")
        self.assertEqual(
            "pending",
            self.connection.execute("SELECT status FROM orders WHERE total = 300").fetchone()[0],
        )

    def test_upgrade_is_idempotent(self) -> None:
        self.migration.upgrade(self.connection)
        self.migration.upgrade(self.connection)

    def test_recovery_decision_is_recorded(self) -> None:
        content = (WORKSPACE / "MIGRATION.md").read_text(encoding="utf-8").lower()
        self.assertTrue("rollback" in content or "forward" in content)


if __name__ == "__main__":
    unittest.main()

