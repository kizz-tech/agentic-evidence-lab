# Reject invalid request limits

The request parser currently accepts negative limits and later fails deep in
pagination. Repair the causal defect in `parse_limit` while preserving valid
integer inputs. A limit must be between 1 and 100 inclusive.
