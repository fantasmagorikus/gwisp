import datetime as dt
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from gwisp.config import AppSettings, RegionSettings
from gwisp.ui import pyside_app
from gwisp.ui.pyside_app import (
    MAIN_BUTTONS,
    CaptureBoxWindow,
    GwispWindow,
    load_app_icon,
    parse_answer_history_entry,
    parse_connect_command,
)


def test_app_icon_asset_loads() -> None:
    QApplication.instance() or QApplication([])

    icon = load_app_icon()

    assert not icon.isNull()


def test_main_toolbar_has_sync_ocr_button() -> None:
    assert any(
        text_key == "button.sync_ocr" and command == "sync_ocr"
        for text_key, command, _ in MAIN_BUTTONS
    )
    assert any(
        text_key == "button.support" and command == "show_support"
        for text_key, command, _ in MAIN_BUTTONS
    )
    assert any(
        text_key == "button.test_ai_provider" and command == "test_ai_provider"
        for text_key, command, _ in MAIN_BUTTONS
    )


def test_capture_box_does_not_take_focus_when_shown() -> None:
    QApplication.instance() or QApplication([])
    box = CaptureBoxWindow(RegionSettings(left=10, top=20, width=320, height=180))

    try:
        assert box.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        assert box.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    finally:
        box.close()


def test_final_answers_are_stacked_with_checkmarks(monkeypatch, tmp_path) -> None:
    QApplication.instance() or QApplication([])

    settings = AppSettings(
        output_log_file=str(tmp_path / "qa.log"),
        event_log_file=str(tmp_path / "events.log"),
    )

    class FakeTesseractOcr:
        tesseract_path = None

        def __init__(self, _settings):
            pass

    class FakeScreenCapture:
        pass

    class FakeWindowCapture:
        pass

    class FakeLlmClient:
        display_name = "Local Ollama"
        model_name = "fake-local-model"

        def warm_up(self):
            return "ready"

        def ask(self, _question):
            return "Answer: B"

    monkeypatch.setattr(pyside_app, "load_settings", lambda: settings)
    monkeypatch.setattr(pyside_app, "TesseractOcr", FakeTesseractOcr)
    monkeypatch.setattr(pyside_app, "MssScreenCapture", FakeScreenCapture)
    monkeypatch.setattr(pyside_app, "WindowCapture", FakeWindowCapture)
    monkeypatch.setattr(pyside_app, "create_llm_client", lambda _settings: FakeLlmClient())

    window = GwispWindow()
    captured_at = dt.datetime(2026, 4, 27, 9, 30, 0)

    try:
        assert not window.windowIcon().isNull()
        assert "Alpha build 1.0.3" in window.windowTitle()
        assert window.language_combo.currentData() == "en"
        assert window.toolbar_buttons["button.sync_ocr"].text() == "Sync OCR"
        assert window.toolbar_buttons["button.test_ai_provider"].text() == "Test AI"
        assert window.provider_label.text() == "AI provider: Local Ollama (fake-local-model)"
        signature_labels = [label.text() for label in window.status_bar.findChildren(QLabel)]
        assert any("> developed by @fantasmagorikus" in text for text in signature_labels)
        window.handle_ui_event(
            ("final_answer", "Question 1", "Answer: B\nReason: test", captured_at)
        )
        window.handle_ui_event(("final_answer", "Question 2", "Answer: C", captured_at))
        window.handle_ui_event(
            (
                "final_answer",
                "Question 3",
                "The question needs to be captured again.",
                captured_at,
            )
        )

        assert window.answer_history_list.count() == 2
        first_widget = window.answer_history_list.itemWidget(window.answer_history_list.item(0))
        second_widget = window.answer_history_list.itemWidget(window.answer_history_list.item(1))
        assert first_widget.toggle_button.text() == "1 - ✅ Answer: B"
        assert first_widget.reason_label.text() == "Reason: test"
        assert first_widget.reason_label.isHidden()
        first_widget.toggle_button.setChecked(True)
        assert not first_widget.reason_label.isHidden()
        assert second_widget.toggle_button.text() == "2 - ✅ Answer: C"
        assert second_widget.reason_label.text() == ""
        assert window.right_side_layout.indexOf(window.preview_frame) == 0
        assert window.right_side_layout.indexOf(window.answer_history_frame) == 1

        window.clear_views()

        assert window.answer_history_list.count() == 0
        window.handle_ui_event(("final_answer", "Question 4", "Answer: A", captured_at))
        restarted_widget = window.answer_history_list.itemWidget(window.answer_history_list.item(0))
        assert restarted_widget.toggle_button.text() == "1 - ✅ Answer: A"
    finally:
        window.close()


def test_capture_ocr_image_prefers_remote_sync_capture(monkeypatch, tmp_path) -> None:
    QApplication.instance() or QApplication([])

    settings = AppSettings(
        output_log_file=str(tmp_path / "qa.log"),
        event_log_file=str(tmp_path / "events.log"),
    )

    class FakeTesseractOcr:
        tesseract_path = None

        def __init__(self, _settings):
            pass

    class FakeScreenCapture:
        def capture_region_image(self, _region):
            raise AssertionError("local capture should not be used while Sync OCR is connected")

    class FakeWindowCapture:
        pass

    class FakeLlmClient:
        display_name = "Cloud API"
        model_name = "cloud-model"

        def warm_up(self):
            return "ready"

        def ask(self, _question):
            return "Answer: B"

    class FakeRemoteSyncCapture:
        connection_info = None

        def capture_region_image(self, _region):
            return pyside_app.Image.new("RGB", (7, 5), "white")

    monkeypatch.setattr(pyside_app, "load_settings", lambda: settings)
    monkeypatch.setattr(pyside_app, "TesseractOcr", FakeTesseractOcr)
    monkeypatch.setattr(pyside_app, "MssScreenCapture", FakeScreenCapture)
    monkeypatch.setattr(pyside_app, "WindowCapture", FakeWindowCapture)
    monkeypatch.setattr(pyside_app, "create_llm_client", lambda _settings: FakeLlmClient())

    window = GwispWindow()
    try:
        window.remote_sync_capture = FakeRemoteSyncCapture()

        assert window.capture_mode() == "sync_ocr"
        assert window.capture_ocr_image().size == (7, 5)
    finally:
        window.close()


def test_parse_answer_history_entry_splits_summary_reason_and_skips_recapture() -> None:
    entry = parse_answer_history_entry("Answer: D\nReason: Because the option matches.")

    assert entry is not None
    assert entry.summary == "Answer: D"
    assert entry.reason == "Reason: Because the option matches."

    assert parse_answer_history_entry("The question needs to be captured again.") is None


def test_parse_connect_command_returns_argv_without_shell_metachar_execution() -> None:
    argv = parse_connect_command('mstsc /v:example-host "&" calc')

    assert argv == ["mstsc", "/v:example-host", "&", "calc"]
