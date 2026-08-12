# Add member pricing

Extend `price_after_discount` with an optional `member` flag. Members receive
an additional five percentage points of discount. The final discount must
remain between zero and one hundred percent, and existing callers must keep
their behavior.
