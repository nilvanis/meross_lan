# Why?

While tests aren't required to publish a custom component for Home Assistant, they will generally make development easier because good tests will expose when changes you want to make to the component logic will break expected functionality. Home Assistant uses [`pytest`](https://docs.pytest.org/en/latest/) for its tests, and the tests that have been included are modeled after tests that are written for core Home Assistant integrations. These tests pass with 100% coverage (unless something has changed ;) ) and have comments to help you understand the purpose of different parts of the test.

# Getting Started

To begin, it is recommended to create a virtual environment to install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
```

You can then install the dependencies that will allow you to run tests:
`pip3 install -r requirements_test.txt.`

This will install `homeassistant`, `pytest`, and `pytest-homeassistant`, a plugin which allows you to leverage helpers that are available in Home Assistant for core integration tests.

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
`pytest tests/test_init.py -k test_setup_unload_and_reload_entry` | Runs the `test_setup_unload_and_reload_entry` test function located in `tests/test_init.py`
`pytest tests/test_climate_schedule.py` | Runs the AUTO HVAC mode and schedule regression tests
`pytest tests/test_ha_logging.py` | Verifies that unknown HA warnings/errors fail tests across the full test lifecycle
