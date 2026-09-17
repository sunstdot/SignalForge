# Wingsbot invoke migration final fixes

Status: complete

## Changes

- Last30Days and venture-product-radar now create a unique UUID output directory for each invocation.
- Each prompt writes into that directory, the artifact glob is scoped to it, and artifact validation uses the same directory.
- Direct venture-product-radar script execution remains unchanged.
- Wingsbot setup now builds a dependency-free wheel as a local preparation check before uninstalling either existing distribution. Build isolation is disabled so this check does not fetch build dependencies.

## TDD evidence

- Added concurrent-invocation regressions for both importers. Before implementation, both failed because two calls selected the same artifact.
- Added a fake-interpreter setup regression. Before implementation, setup returned success after invoking uninstall without attempting wheel preparation.
- After implementation, all focused migration tests pass.

## Verification

- `backend/venv/bin/python -m pytest -q backend/tests/test_wingsbot_client.py backend/tests/test_last30days_importer.py backend/tests/test_venture_product_radar_importer.py backend/tests/test_wingsbot_setup.py`: 45 passed.
- `backend/venv/bin/python -m py_compile backend/services/last30days_importer.py backend/services/venture_product_radar_importer.py`: passed.
- `zsh -n scripts/setup-wingsbot.zsh`: passed.
- Scoped `git diff --check`: passed.

No network or model calls were made.
