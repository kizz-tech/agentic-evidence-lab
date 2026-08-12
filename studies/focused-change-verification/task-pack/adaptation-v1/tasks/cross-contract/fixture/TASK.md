# Task: add a family-name display order

Extend `format_user` with a keyword-only `order` argument. Keep the current
`given` order as the default, support `family` as `Family, Given`, and raise
`ValueError` for unsupported values. Add `welcome_formal` in `welcome.py` and
make it use family order without changing `welcome`. Validate both the owning
formatter contract and its direct consumer.

