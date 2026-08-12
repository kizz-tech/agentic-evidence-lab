# Correct blocked-state formatting

Users report that failed jobs are displayed as ready. Update this small module
so ready records retain the current `ready:<id>` format while failed records
display `blocked:<reason>`. Keep the public API stable.
