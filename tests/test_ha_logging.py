"""Exercise the log guard with messages unrelated to any known HA deprecation."""

from pathlib import Path

import pytest


@pytest.fixture
def guarded_pytester(pytester, monkeypatch):
    # Copy just the guard, without the integration fixtures or HA test plugin.
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    pytester.makeconftest(
        Path(__file__).with_name("ha_logging.py").read_text(encoding="utf-8")
    )
    pytester.makeini("[pytest]\naddopts = -p no:sugar\n")
    return pytester


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
@pytest.mark.parametrize("level", ["warning", "error"])
def test_unknown_ha_logs_fail(guarded_pytester, phase, level):
    guarded_pytester.makepyfile(f"""
        import logging
        import pytest

        def report_problem():
            logging.getLogger("homeassistant.future_api").{level}("Previously unknown problem")

        @pytest.fixture
        def lifecycle():
            if {phase!r} == "setup":
                report_problem()
            yield
            if {phase!r} == "teardown":
                report_problem()

        def test_integration(lifecycle, caplog):
            if {phase!r} == "call":
                report_problem()
            caplog.clear()
        """)
    result = guarded_pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(
        ["*Unexpected Home Assistant logs:*", "*Previously unknown problem*"]
    )


def test_only_exact_loader_notice_is_allowed(guarded_pytester):
    guarded_pytester.makepyfile("""
        import logging
        from conftest import CUSTOM_INTEGRATION_NOTICE

        def test_normal_logs():
            logging.getLogger("homeassistant.loader").warning(CUSTOM_INTEGRATION_NOTICE)
            logging.getLogger("homeassistant.future_api").info("Normal operation")

        def test_other_loader_warning():
            logging.getLogger("homeassistant.loader").warning("New loader problem")

        def test_same_message_from_other_logger():
            logging.getLogger("homeassistant.future_api").warning(CUSTOM_INTEGRATION_NOTICE)

        def test_loader_error():
            logging.getLogger("homeassistant.loader").error(CUSTOM_INTEGRATION_NOTICE)
        """)
    result = guarded_pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=4, errors=3)


def test_guard_starts_before_dynamic_hass_and_finishes_after_shutdown(guarded_pytester):
    with (guarded_pytester.path / "conftest.py").open(
        "a", encoding="utf-8"
    ) as conftest:
        conftest.write("""

@pytest.fixture
def hass():
    logging.getLogger("homeassistant.core").warning("Startup problem")
    yield
    logging.getLogger("homeassistant.core").error("Shutdown problem")

@pytest.fixture(autouse=True)
def auto_enable(request, fail_on_ha_logs):
    # Match the real suite's dynamic fixture lookup and teardown ordering.
    request.getfixturevalue("hass")
    yield
""")
    guarded_pytester.makepyfile("def test_integration(): pass")
    result = guarded_pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*Startup problem*", "*Shutdown problem*"])
