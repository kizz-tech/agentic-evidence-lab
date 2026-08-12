# Task: migrate existing orders to a required status

Implement `migrations/002_add_status.py`. Upgrade a populated v1 SQLite database
so `orders.status` is non-null, existing rows become `pending`, new rows default
to `pending`, and calling `upgrade` again is safe. Do not alter `create_v1`.
Record the rollback or forward-repair decision in `MIGRATION.md`. Validate the
migration against a disposable populated database and report the exact state.

