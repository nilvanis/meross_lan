# Why?

Tests help catch changes that break integration behavior. Home Assistant uses
[`pytest`](https://docs.pytest.org/en/latest/), and this repository uses
`pytest-homeassistant-custom-component` to access its integration test helpers.

# Getting Started

The test environment is pinned to stable Home Assistant **2026.10.4** and
`pytest-homeassistant-custom-component` **0.13.375**, using Python **3.14.10**.
Home Assistant 2026.10.4 requires Python 3.14.2 or later. CI reads the interpreter
version from `.python-version`; the devcontainer image is pinned to the same
Python patch. Install Python 3.14.10, then create a virtual environment:

```bash
python3.14 -m venv venv
source venv/bin/activate
python -m pip install -r requirements_test.txt
```

`requirements_dev.txt` pins Home Assistant and `requirements_test.txt` pins its
matching test helper package. Update the pair together; leaving either dependency
unconstrained can introduce a newer Home Assistant or a beta into the test run.

Version sources: [Home Assistant](https://pypi.org/project/homeassistant/2026.10.4/),
[test helpers](https://pypi.org/project/pytest-homeassistant-custom-component/0.13.375/),
[Python](https://www.python.org/downloads/release/python-31410/).

# Useful commands

Command | Description
------- | -----------
`pytest tests/` | This will run all tests in `tests/` and tell you how many passed/failed
`pytest --durations=10 --cov-report term-missing --cov=custom_components.meross_lan tests` | This tells `pytest` that your target module to test is `custom_components.meross_lan` so that it can give you a [code coverage](https://en.wikipedia.org/wiki/Code_coverage) summary, including % of code that was executed and the line numbers of missed executions.
`pytest tests/test_climate_schedule.py` | Runs the AUTO HVAC mode and schedule regression tests
