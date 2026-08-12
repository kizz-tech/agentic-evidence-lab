# Repair saved-message feedback

The local form saves successfully, but users never see the confirmation text.
Repair the page and add `e2e_test.py`, an executable deterministic check that
would fail for the reported regression and pass after the repair. Use only the
Python standard library in this calibration fixture.
