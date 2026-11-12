# Why?

Tests help catch changes that break integration behavior. Home Assistant uses
[`pytest`](https://docs.pytest.org/en/latest/), and this repository uses its
official `pytest-homeassistant` package to access the integration test helpers.

# Getting Started

The test environment follows upstream: Home Assistant and `pytest-homeassistant`
are pinned to the same release (currently **2026.11.0**) in `requirements_test.txt`,
using Python **3.14.10**. Home Assistant 2026.11 requires Python 3.14.2 or later.
CI reads the interpreter
version from `.python-version`; the devcontainer image is pinned to the same
Python patch. Install Python 3.14.10, then create a virtual environment:

```bash
python3.14 -m venv venv
source venv/bin/activate
python -m pip install -r requirements_test.txt
```

Both pins come from upstream and change with upstream imports. Keep the two
versions equal: each `pytest-homeassistant` release matches the Home Assistant
release of the same number.

Version sources: [Home Assistant](https://pypi.org/project/homeassistant/2026.11.0/),
[test helpers](https://pypi.org/project/pytest-homeassistant/2026.11.0/),
[Python](https://www.python.org/downloads/release/python-31410/).

# Home Assistant compatibility checks

Every test fails on unexpected `WARNING`, `ERROR` or `CRITICAL` logs from
`homeassistant` and its child loggers. This includes future API deprecations from
`homeassistant.helpers.frame`, without matching a particular message, API or
removal date. Capture starts before Home Assistant setup and remains active
through shutdown. It uses an independent handler, so clearing `caplog` or consuming
logs in integration helpers cannot hide a problem.

The only exception is the exact loader warning announcing that `meross_lan` is a
custom integration. Other loader warnings and errors still fail tests. Tests of
the guard inject arbitrary warnings/errors during setup, execution and teardown.

Previously, the integration's log helper only printed warnings from its own
logger. Home Assistant compatibility reports are log messages, not Python
warnings, and did not fail tests even when device setup exercised the affected
code. The general guard exposed the deprecated `via_device` argument, hub registry
mapping lookups, and firmware entities attached to devices without unique IDs.

These checks cover code paths exercised by tests on the installed Home Assistant
version. Newer Core releases are checked when an upstream import updates the pins;
the daily workflow also uses those pins and does not select new versions automatically.

# Useful commands

Command | Description
------- | -----------
`pytest tests/` | This will run all tests in `tests/` and tell you how many passed/failed
`pytest --durations=10 --cov-report term-missing --cov=custom_components.meross_lan tests` | This tells `pytest` that your target module to test is `custom_components.meross_lan` so that it can give you a [code coverage](https://en.wikipedia.org/wiki/Code_coverage) summary, including % of code that was executed and the line numbers of missed executions.
`pytest tests/test_climate_schedule.py` | Runs the AUTO HVAC mode and schedule regression tests
`pytest tests/test_ha_logging.py` | Verifies that unknown HA warnings/errors fail tests across the full test lifecycle
