import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gwisp.config import AppSettings
from gwisp.ui import sync_ocr_app
from gwisp.ui.sync_ocr_app import SyncOcrWindow


def test_sync_ocr_window_uses_main_app_xp_design_primitives() -> None:
    QApplication.instance() or QApplication([])
    window = SyncOcrWindow()

    try:
        assert window.warning_label.objectName() == "warningLabel"
        assert window.button_bar.objectName() == "buttonBar"
        assert window.support_button.text() == "Support"
        assert window.details_frame.title() == "Sync OCR details"
        assert window.statusBar() is not None
        assert "QGroupBox" in window.styleSheet()
        assert "QFrame#buttonBar" in window.styleSheet()
    finally:
        window.close()


def test_sync_ocr_language_selector_updates_labels(monkeypatch, tmp_path) -> None:
    QApplication.instance() or QApplication([])
    settings = AppSettings(
        language="de",
        output_log_file=str(tmp_path / "qa.log"),
        event_log_file=str(tmp_path / "events.log"),
    )
    saved_languages: list[str] = []
    monkeypatch.setattr(sync_ocr_app, "load_settings", lambda: settings)
    monkeypatch.setattr(sync_ocr_app, "save_language", saved_languages.append)

    window = SyncOcrWindow()

    try:
        assert window.language_combo.currentData() == "de"
        assert window.details_frame.title() == "Sync-OCR-Details"

        window.language_combo.setCurrentIndex(window.language_combo.findData("pt"))

        assert saved_languages == ["pt"]
        assert window.language_label.text() == "Idioma"
        assert window.support_button.text() == "Apoiar"
        assert window.details_frame.title() == "Detalhes do Sync OCR"
    finally:
        window.close()
