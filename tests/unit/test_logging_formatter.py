import json
import logging

import pytest

from app.core.logging import JsonFormatter


@pytest.mark.unit
def test_json_formatter_outputs_expected_fields():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", args=(), exc_info=None)
    record.event = "api"
    record.endpoint = "visit-volume"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert payload["event"] == "api"
    assert payload["endpoint"] == "visit-volume"
    assert "timestamp" in payload
