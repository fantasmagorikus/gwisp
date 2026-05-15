from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gwisp.adapters.sync_capture import SyncCaptureServer, format_sync_details
from gwisp.config import APP_FOOTER_SIGNATURE, load_settings, save_language
from gwisp.i18n import (
    SUPPORTED_LANGUAGES,
    language_index,
    language_label,
    normalized_language,
    translate,
)
from gwisp.ui.pyside_app import (
    XP_CONTROL,
    XP_CONTROL_DARK,
    XP_INFO,
    XP_STATUS_BLUE,
    XP_TEXT,
    XP_WINDOW,
    apply_app_icon,
    configure_windows_app_id,
)
from gwisp.ui.support_dialog import show_support_dialog


class SyncOcrWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.language = normalized_language(self.settings.language)
        self.server: SyncCaptureServer | None = None
        self.loading_step = 0

        self.setWindowTitle(self.tr("window.sync.title"))
        self.resize(520, 340)
        self.setMinimumSize(420, 280)
        apply_app_icon(QApplication.instance(), self)

        self.configure_xp_style()
        self.build_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(450)
        self.timer.timeout.connect(self.update_waiting_status)

    def tr(self, key: str, **format_values: object) -> str:
        return translate(self.language, key, **format_values)

    def configure_xp_style(self) -> None:
        app = QApplication.instance()
        if app:
            app.setFont(QFont("Tahoma", 8))
            app.setStyle("Windows")

        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {XP_CONTROL};
                color: {XP_TEXT};
                font-family: Tahoma;
                font-size: 8pt;
            }}
            QLabel#warningLabel {{
                background: {XP_INFO};
                color: {XP_TEXT};
                border: 1px solid {XP_TEXT};
                padding: 3px 6px;
            }}
            QFrame#buttonBar {{
                background: {XP_CONTROL};
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid {XP_CONTROL_DARK};
                border-bottom: 1px solid {XP_CONTROL_DARK};
            }}
            QPushButton {{
                background: {XP_CONTROL};
                color: {XP_TEXT};
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #404040;
                border-bottom: 1px solid #404040;
                padding: 2px 8px;
                min-height: 20px;
            }}
            QPushButton:pressed {{
                border-top: 1px solid #404040;
                border-left: 1px solid #404040;
                border-right: 1px solid #ffffff;
                border-bottom: 1px solid #ffffff;
                padding-top: 3px;
                padding-left: 9px;
            }}
            QGroupBox {{
                background: {XP_CONTROL};
                border: 2px groove {XP_CONTROL_DARK};
                margin-top: 8px;
                padding: 8px 6px 6px 6px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 0 3px;
                background: {XP_CONTROL};
            }}
            QTextEdit {{
                background: {XP_WINDOW};
                color: {XP_TEXT};
                border: 2px inset {XP_CONTROL_DARK};
                selection-background-color: {XP_STATUS_BLUE};
                selection-color: {XP_WINDOW};
                font-family: Consolas;
                font-size: 9pt;
            }}
            QStatusBar {{
                background: {XP_CONTROL};
                color: {XP_TEXT};
                border-top: 1px solid {XP_CONTROL_DARK};
            }}
            """
        )

    def build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 6, 8, 0)
        layout.setSpacing(6)
        self.setCentralWidget(central)

        self.warning_label = QLabel(self.tr("warning.sync"))
        self.warning_label.setObjectName("warningLabel")
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)

        self.button_bar = QFrame()
        self.button_bar.setObjectName("buttonBar")
        button_layout = QHBoxLayout(self.button_bar)
        button_layout.setContentsMargins(3, 3, 3, 3)
        button_layout.setSpacing(6)

        self.sync_button = QPushButton(self.tr("button.sync_ocr"))
        self.sync_button.setFixedWidth(92)
        self.sync_button.clicked.connect(self.start_sync_server)
        button_layout.addWidget(self.sync_button)

        self.support_button = QPushButton(self.tr("button.support"))
        self.support_button.setFixedWidth(92)
        self.support_button.clicked.connect(self.show_support)
        button_layout.addWidget(self.support_button)
        button_layout.addStretch(1)

        self.language_label = QLabel(self.tr("language.label"))
        button_layout.addWidget(self.language_label)

        self.language_combo = QComboBox()
        for option in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(option.label, option.code)
        self.language_combo.setFixedWidth(140)
        self.language_combo.setCurrentIndex(language_index(self.language))
        self.language_combo.currentIndexChanged.connect(self.change_language)
        button_layout.addWidget(self.language_combo)
        layout.addWidget(self.button_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.status_label.setVisible(False)

        self.details_frame = QGroupBox(self.tr("group.sync_details"))
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setContentsMargins(6, 8, 6, 6)
        details_layout.setSpacing(6)
        details_layout.addWidget(self.status_label)
        self.details_text = QTextEdit()
        self.details_text.setAcceptRichText(False)
        self.details_text.setReadOnly(True)
        self.details_text.setVisible(False)
        self.details_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        details_layout.addWidget(self.details_text, stretch=1)
        layout.addWidget(self.details_frame, stretch=1)

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        signature_label = QLabel(APP_FOOTER_SIGNATURE)
        signature_label.setStyleSheet(
            "QLabel { color: #003300; font-family: Consolas; padding: 0 4px; }"
        )
        self.status_bar.addPermanentWidget(signature_label)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.tr("status.idle_bar"))

    def change_language(self) -> None:
        language = normalized_language(str(self.language_combo.currentData()))
        if language == self.language:
            return

        self.language = language
        self.settings.language = language
        save_language(language)
        self.apply_language()
        if self.server is None:
            self.status_bar.showMessage(
                f"{self.tr('status.prefix')}: "
                f"{self.tr('status.language_changed', language=language_label(language))}"
            )
        else:
            self.update_waiting_status()

    def apply_language(self) -> None:
        self.setWindowTitle(self.tr("window.sync.title"))
        self.warning_label.setText(self.tr("warning.sync"))
        self.sync_button.setText(self.tr("button.sync_ocr"))
        self.support_button.setText(self.tr("button.support"))
        self.language_label.setText(self.tr("language.label"))
        self.details_frame.setTitle(self.tr("group.sync_details"))

        combo_index = language_index(self.language)
        if self.language_combo.currentIndex() != combo_index:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(combo_index)
            self.language_combo.blockSignals(False)

    def start_sync_server(self) -> None:
        if self.server is None:
            self.server = SyncCaptureServer()
            self.server.start()
            self.details_text.setPlainText(format_sync_details(self.server.connection_info))
            self.details_text.setVisible(True)
            self.status_label.setVisible(True)
            self.sync_button.setEnabled(False)
            self.timer.start()

        self.update_waiting_status()

    def show_support(self) -> None:
        show_support_dialog(self, self.language)

    def update_waiting_status(self) -> None:
        if self.server is not None and self.server.is_connected():
            self.status_label.setText(self.tr("status.sync_connected"))
            self.status_bar.showMessage(self.tr("status.sync_connected_bar"))
            return

        dots = "." * (self.loading_step % 4)
        self.loading_step += 1
        self.status_label.setText(self.tr("status.sync_waiting", dots=dots))
        self.status_bar.showMessage(self.tr("status.sync_waiting_bar"))

    def closeEvent(self, event) -> None:
        if self.server is not None:
            self.server.stop()
        super().closeEvent(event)


def main() -> None:
    configure_windows_app_id()
    app = QApplication.instance() or QApplication([])
    apply_app_icon(app)
    window = SyncOcrWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
