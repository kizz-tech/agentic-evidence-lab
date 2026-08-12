# Make the text codec round-trip safely

The length-prefixed text codec works for current examples but corrupts some
valid user names. Repair it without changing the one-byte length-prefix format.
Reject payloads that cannot be represented by that format.
