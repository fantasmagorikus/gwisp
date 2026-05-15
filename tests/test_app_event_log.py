import json

from gwisp.adapters.app_event_log import ApplicationEventLog


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_event_log_records_structured_events(tmp_path) -> None:
    log_path = tmp_path / "events.log"
    event_log = ApplicationEventLog(log_path)

    event_log.info("capture.started", mode="window", hwnd=123)

    events = read_events(log_path)
    assert len(events) == 1
    assert events[0]["level"] == "INFO"
    assert events[0]["event"] == "capture.started"
    assert events[0]["context"] == {"mode": "window", "hwnd": 123}
    assert "timestamp" in events[0]


def test_event_log_records_exception_details(tmp_path) -> None:
    log_path = tmp_path / "events.log"
    event_log = ApplicationEventLog(log_path)

    try:
        raise RuntimeError("capture failed")
    except RuntimeError as exc:
        event_log.exception("capture.error", exc, mode="ocr_box")

    event = read_events(log_path)[0]
    assert event["level"] == "ERROR"
    assert event["event"] == "capture.error"
    assert event["context"]["mode"] == "ocr_box"
    assert event["context"]["error_type"] == "RuntimeError"
    assert event["context"]["error"] == "capture failed"


def test_event_log_rotates_when_file_is_too_large(tmp_path) -> None:
    log_path = tmp_path / "events.log"
    log_path.write_text("x" * 80, encoding="utf-8")
    event_log = ApplicationEventLog(log_path, max_bytes=50, backup_count=1)

    event_log.info("app.started")

    assert (tmp_path / "events.log.1").exists()
    assert read_events(log_path)[0]["event"] == "app.started"
