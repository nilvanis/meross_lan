"""Fail integration tests on unexpected Home Assistant warnings and errors."""

import logging

import pytest

CUSTOM_INTEGRATION_NOTICE = (
    "We found a custom integration meross_lan which has not been tested by Home "
    "Assistant. This component might cause stability problems, be sure to disable "
    "it if you experience issues with Home Assistant"
)


class HomeAssistantLogHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord):
        # This notice is emitted for every custom integration, including healthy ones.
        if (
            record.name == "homeassistant.loader"
            and record.levelno == logging.WARNING
            and record.getMessage() == CUSTOM_INTEGRATION_NOTICE
        ):
            return
        self.records.append(record)


@pytest.fixture(autouse=True)
def fail_on_ha_logs():
    """Keep independent records: caplog.clear/pop_logs must not hide HA problems."""
    logger = logging.getLogger("homeassistant")
    handler = HomeAssistantLogHandler()
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()

    if handler.records:
        messages = "\n".join(
            f"{record.levelname} {record.name}: {record.getMessage()}"
            for record in handler.records
        )
        pytest.fail(f"Unexpected Home Assistant logs:\n{messages}", pytrace=False)
