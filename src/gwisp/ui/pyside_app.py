import ctypes
import datetime
import queue
import shlex
import subprocess  # nosec B404
import threading
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources

from PIL import Image
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QIcon,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwisp.adapters.app_event_log import ApplicationEventLog
from gwisp.adapters.llm_clients import create_llm_client
from gwisp.adapters.log_store import FileLogStore
from gwisp.adapters.ocr_tesseract import TesseractOcr
from gwisp.adapters.screen_mss import MssScreenCapture
from gwisp.adapters.sync_capture import RemoteSyncScreenCapture, parse_sync_details
from gwisp.adapters.window_capture import WindowCapture, WindowInfo
from gwisp.config import (
    APP_DIR,
    APP_FOOTER_SIGNATURE,
    RegionSettings,
    load_settings,
    save_language,
)
from gwisp.i18n import (
    SUPPORTED_LANGUAGES,
    language_index,
    language_label,
    normalized_language,
    translate,
)
from gwisp.services.qa_pipeline import QAPipeline
from gwisp.services.text_cleaner import (
    APP_WINDOW_STATUS,
    clean_ocr_text,
    compact_length,
    looks_like_app_window,
)
from gwisp.ui.support_dialog import show_support_dialog

XP_CONTROL = "#ece9d8"
XP_CONTROL_DARK = "#aca899"
XP_INFO = "#ffffe1"
XP_WINDOW = "#ffffff"
XP_TEXT = "#000000"
XP_STATUS_BLUE = "#0a246a"
APP_USER_MODEL_ID = "Gwisp.Desktop"
APP_ICON_RESOURCE = ("assets", "gwisp_xp.ico")

MAIN_BUTTONS = [
    ("button.connect_remote", "connect_remote", 92),
    ("button.select_capture_window", "select_capture_window", 148),
    ("button.sync_ocr", "sync_ocr", 82),
    ("button.ocr_box", "show_capture_box", 82),
    ("button.start", "start_capture", 74),
    ("button.pause", "pause_capture", 74),
    ("button.clear", "clear_views", 74),
    ("button.save_log_now", "save_log_now", 112),
    ("button.test_ocr_once", "test_ocr_once", 112),
    ("button.check_setup", "check_setup", 100),
    ("button.load_model", "load_ai_model", 104),
    ("button.test_ai_provider", "test_ai_provider", 112),
    ("button.support", "show_support", 88),
]


RECAPTURE_MESSAGE = "the question needs to be captured again"


def load_app_icon() -> QIcon:
    icon_resource = resources.files("gwisp").joinpath(*APP_ICON_RESOURCE)
    with resources.as_file(icon_resource) as icon_path:
        return QIcon(str(icon_path))


def apply_app_icon(app: QApplication | None, window: QWidget | None = None) -> None:
    icon = load_app_icon()
    if icon.isNull():
        return
    if app is not None:
        app.setWindowIcon(icon)
    if window is not None:
        window.setWindowIcon(icon)


def configure_windows_app_id() -> None:
    if not hasattr(ctypes, "windll"):
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except OSError:
        return


def parse_connect_command(command: str) -> list[str]:
    command = command.strip()
    if not command:
        return []
    if hasattr(ctypes, "windll"):
        return parse_windows_command_line(command)
    return shlex.split(command)


def parse_windows_command_line(command: str) -> list[str]:
    argc = ctypes.c_int()
    ctypes.windll.shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    argv = ctypes.windll.shell32.CommandLineToArgvW(command, ctypes.byref(argc))
    if not argv:
        raise ValueError("could not parse connect_command")
    try:
        return [argv[index] for index in range(argc.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)


@dataclass(frozen=True)
class AnswerHistoryEntry:
    summary: str
    reason: str = ""


def parse_answer_history_entry(answer: str) -> AnswerHistoryEntry | None:
    cleaned = answer.strip()
    if not cleaned or RECAPTURE_MESSAGE in cleaned.lower():
        return None

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return None

    answer_index = next(
        (index for index, line in enumerate(lines) if line.lower().startswith("answer:")),
        0,
    )
    answer_line = lines[answer_index]
    summary = answer_line if answer_line.lower().startswith("answer:") else f"Answer: {answer_line}"

    reason_index = next(
        (index for index, line in enumerate(lines) if line.lower().startswith("reason:")),
        None,
    )
    if reason_index is not None:
        reason = "\n".join(lines[reason_index:])
    else:
        reason = "\n".join(line for index, line in enumerate(lines) if index != answer_index)

    return AnswerHistoryEntry(summary=summary, reason=reason)


class AnswerHistoryWidget(QWidget):
    def __init__(
        self,
        number: int,
        entry: AnswerHistoryEntry,
        on_size_changed: Callable[[], None],
    ) -> None:
        super().__init__()
        self.on_size_changed = on_size_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.toggle_button = QToolButton()
        self.toggle_button.setText(f"{number} - ✅ {entry.summary}")
        self.toggle_button.setCheckable(bool(entry.reason))
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.setStyleSheet("QToolButton { text-align: left; padding: 2px; }")
        layout.addWidget(self.toggle_button)

        self.reason_label = QLabel(entry.reason)
        self.reason_label.setWordWrap(True)
        self.reason_label.setVisible(False)
        self.reason_label.setContentsMargins(18, 0, 2, 4)
        layout.addWidget(self.reason_label)

        self.toggle_button.toggled.connect(self.set_reason_visible)

    def set_reason_visible(self, checked: bool) -> None:
        self.reason_label.setVisible(checked)
        self.on_size_changed()


class WindowPickerDialog(QDialog):
    def __init__(
        self,
        window_capture: WindowCapture,
        exclude_hwnds: set[int],
        parent: QWidget | None = None,
        language: str = "en",
    ) -> None:
        super().__init__(parent)
        self.language = normalized_language(language)
        self.window_capture = window_capture
        self.exclude_hwnds = exclude_hwnds
        self.selected_window: WindowInfo | None = None

        self.setWindowTitle(translate(self.language, "dialog.window_picker.title"))
        self.resize(640, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.accept_selected_window)
        layout.addWidget(self.list_widget)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        refresh_button = button_box.addButton(
            translate(self.language, "dialog.window_picker.refresh"),
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        refresh_button.clicked.connect(self.populate_windows)
        button_box.accepted.connect(self.accept_selected_window)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.populate_windows()

    def populate_windows(self) -> None:
        self.list_widget.clear()
        for window in self.window_capture.list_windows():
            if window.hwnd in self.exclude_hwnds:
                continue

            item = QListWidgetItem(window.display_name)
            item.setData(Qt.ItemDataRole.UserRole, window)
            self.list_widget.addItem(item)

        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def accept_selected_window(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return

        self.selected_window = item.data(Qt.ItemDataRole.UserRole)
        self.accept()


class SyncOcrDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, language: str = "en") -> None:
        super().__init__(parent)
        self.language = normalized_language(language)
        self.setWindowTitle(translate(self.language, "dialog.sync.title"))
        self.resize(430, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        instructions = QLabel(translate(self.language, "dialog.sync.instructions"))
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.details_text = QTextEdit()
        self.details_text.setAcceptRichText(False)
        self.details_text.setPlaceholderText(
            "Gwisp Sync OCR\nHost: 192.168.1.50\nPort: 49152\nToken: ..."
        )
        layout.addWidget(self.details_text)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            translate(self.language, "dialog.sync.connect")
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def sync_details(self) -> str:
        return self.details_text.toPlainText()


class CaptureBoxWindow(QWidget):
    region_changed = Signal(object)
    closed = Signal()

    BORDER = 6
    GRIP = 22
    MIN_CAPTURE_WIDTH = 220
    MIN_CAPTURE_HEIGHT = 100

    def __init__(self, initial_region: RegionSettings) -> None:
        super().__init__(
            None,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setWindowTitle("Gwisp OCR box")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        self.drag_mode: str | None = None
        self.drag_start = QPoint()
        self.start_geometry = QRect()

        capture_width = min(max(initial_region.width, 360), 640)
        capture_height = min(max(initial_region.height, 140), 320)
        self.resize(capture_width + self.BORDER * 2, capture_height + self.BORDER * 2)
        self.setMinimumSize(
            self.MIN_CAPTURE_WIDTH + self.BORDER * 2,
            self.MIN_CAPTURE_HEIGHT + self.BORDER * 2,
        )
        self.move(initial_region.left, initial_region.top)

    def capture_region(self) -> RegionSettings:
        geometry = self.geometry()
        return RegionSettings(
            left=max(0, geometry.x() + self.BORDER),
            top=max(0, geometry.y() + self.BORDER),
            width=max(1, geometry.width() - self.BORDER * 2),
            height=max(1, geometry.height() - self.BORDER * 2),
        )

    def emit_region(self) -> None:
        self.region_changed.emit(self.capture_region())

    def grip_rect(self) -> QRect:
        return QRect(self.width() - self.GRIP, self.height() - self.GRIP, self.GRIP, self.GRIP)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(QColor("#ffcc00"), 2))
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        painter.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DashLine))
        painter.drawRect(
            self.BORDER - 1,
            self.BORDER - 1,
            self.width() - self.BORDER * 2 + 1,
            self.height() - self.BORDER * 2 + 1,
        )
        painter.setPen(QPen(QColor("#ffcc00"), 2))
        for offset in (6, 11, 16):
            painter.drawLine(
                self.width() - offset,
                self.height() - 3,
                self.width() - 3,
                self.height() - offset,
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.drag_start = event.globalPosition().toPoint()
        self.start_geometry = self.geometry()
        self.drag_mode = (
            "resize" if self.grip_rect().contains(event.position().toPoint()) else "move"
        )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_mode and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.drag_start
            if self.drag_mode == "resize":
                self.resize(
                    max(self.minimumWidth(), self.start_geometry.width() + delta.x()),
                    max(self.minimumHeight(), self.start_geometry.height() + delta.y()),
                )
            else:
                self.move(self.start_geometry.topLeft() + delta)
            return

        cursor = (
            Qt.CursorShape.SizeFDiagCursor
            if self.grip_rect().contains(event.position().toPoint())
            else Qt.CursorShape.SizeAllCursor
        )
        self.setCursor(cursor)

    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        self.drag_mode = None
        self.emit_region()

    def moveEvent(self, _event) -> None:
        self.emit_region()

    def resizeEvent(self, _event) -> None:
        self.emit_region()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()
        super().closeEvent(event)


class GwispWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.language = normalized_language(self.settings.language)
        self.output_log_path = self.settings.resolve_output_path()
        self.event_log_path = self.settings.resolve_event_log_path()
        self.event_log = ApplicationEventLog(self.event_log_path)
        self.event_log.info(
            "app.started",
            app_dir=APP_DIR,
            event_log_path=self.event_log_path,
            output_log_path=self.output_log_path,
        )

        self.ocr_engine = TesseractOcr(self.settings)
        self.tesseract_path = self.ocr_engine.tesseract_path
        self.screen_capture = MssScreenCapture()
        self.window_capture = WindowCapture()
        self.llm_client = create_llm_client(self.settings)
        self.pipeline = QAPipeline(
            settings=self.settings,
            screen_capture=self.screen_capture,
            ocr_engine=self.ocr_engine,
            llm_client=self.llm_client,
        )
        self.log_store = FileLogStore(self.output_log_path)

        self.ui_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.ocr_thread: threading.Thread | None = None
        self.processing_lock = threading.Lock()
        self.processing = False
        self.llm_ready = False
        self.capture_box: CaptureBoxWindow | None = None
        self.capture_region_lock = threading.Lock()
        self.active_capture_region = self.settings.region
        self.capture_window_lock = threading.Lock()
        self.selected_capture_window: WindowInfo | None = None
        self.remote_sync_capture: RemoteSyncScreenCapture | None = None

        self.setWindowTitle(self.tr("window.main.title"))
        apply_app_icon(QApplication.instance(), self)
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.settings.always_on_top)

        self.configure_xp_style()
        self.build_ui()

        self.drain_timer = QTimer(self)
        self.drain_timer.setInterval(100)
        self.drain_timer.timeout.connect(self.drain_ui_queue)
        self.drain_timer.start()

        self.set_status(self.tr("status.idle"))
        if self.tesseract_path:
            self.set_status(self.tr("status.ready_tesseract", path=self.tesseract_path))
        self.event_log.info(
            "app.ready",
            tesseract_path=self.tesseract_path,
            llm_provider=self.llm_provider_name(),
            llm_model=self.llm_model_name(),
            ocr_lang=self.settings.ocr_lang,
        )

    def tr(self, key: str, **format_values: object) -> str:
        return translate(self.language, key, **format_values)

    def llm_provider_name(self) -> str:
        return str(getattr(self.llm_client, "display_name", self.settings.llm_provider))

    def llm_model_name(self) -> str:
        return str(getattr(self.llm_client, "model_name", "configured model"))

    def llm_provider_summary(self) -> str:
        return self.tr(
            "llm.provider",
            provider=self.llm_provider_name(),
            model=self.llm_model_name(),
        )

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
            QLabel#providerLabel {{
                background: {XP_WINDOW};
                color: {XP_TEXT};
                border: 1px solid {XP_CONTROL_DARK};
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
            QListWidget {{
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
                border: 1px inset {XP_CONTROL_DARK};
            }}
            QSplitter::handle {{
                background: {XP_CONTROL};
                width: 6px;
            }}
            QLabel#previewLabel {{
                background: {XP_WINDOW};
                color: {XP_TEXT};
                border: 2px inset {XP_CONTROL_DARK};
                font-family: Consolas;
                font-size: 8pt;
            }}
            """
        )

    def build_ui(self) -> None:
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 6, 8, 0)
        root_layout.setSpacing(6)
        self.setCentralWidget(central)

        self.warning_label = QLabel(self.tr("warning.main"))
        self.warning_label.setObjectName("warningLabel")
        self.warning_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root_layout.addWidget(self.warning_label)

        self.provider_label = QLabel(self.llm_provider_summary())
        self.provider_label.setObjectName("providerLabel")
        self.provider_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root_layout.addWidget(self.provider_label)

        button_bar = QFrame()
        button_bar.setObjectName("buttonBar")
        button_bar_layout = QVBoxLayout(button_bar)
        button_bar_layout.setContentsMargins(3, 3, 3, 3)
        button_bar_layout.setSpacing(3)
        primary_button_layout = QHBoxLayout()
        primary_button_layout.setSpacing(6)
        secondary_button_layout = QHBoxLayout()
        secondary_button_layout.setSpacing(6)
        button_bar_layout.addLayout(primary_button_layout)
        button_bar_layout.addLayout(secondary_button_layout)

        self.toolbar_buttons: dict[str, QPushButton] = {}
        for index, (text_key, command_name, width) in enumerate(MAIN_BUTTONS):
            button = QPushButton(self.tr(text_key))
            button.setFixedWidth(width)
            button.clicked.connect(self.qt_slot(getattr(self, command_name)))
            target_layout = primary_button_layout if index < 7 else secondary_button_layout
            target_layout.addWidget(button)
            self.toolbar_buttons[text_key] = button
        primary_button_layout.addStretch(1)

        self.language_label = QLabel(self.tr("language.label"))
        primary_button_layout.addWidget(self.language_label)

        self.language_combo = QComboBox()
        for option in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(option.label, option.code)
        self.language_combo.setFixedWidth(140)
        self.language_combo.setCurrentIndex(language_index(self.language))
        self.language_combo.currentIndexChanged.connect(self.change_language)
        primary_button_layout.addWidget(self.language_combo)
        secondary_button_layout.addStretch(1)
        root_layout.addWidget(button_bar)

        content = QWidget()
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        content_layout.setRowStretch(0, 3)
        content_layout.setRowStretch(1, 2)
        content_layout.setColumnStretch(0, 1)
        content_layout.setColumnStretch(1, 0)
        root_layout.addWidget(content, stretch=1)

        top_splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(top_splitter, 0, 0)

        self.question_frame = self.create_group_box(self.tr("group.question"))
        self.answer_frame = self.create_group_box(self.tr("group.answer"))
        self.question_text = self.create_text_box()
        self.answer_text = self.create_text_box()
        self.question_frame.layout().addWidget(self.question_text)
        self.answer_frame.layout().addWidget(self.answer_text)
        top_splitter.addWidget(self.question_frame)
        top_splitter.addWidget(self.answer_frame)
        top_splitter.setSizes([1, 1])

        self.log_frame = self.create_group_box(self.tr("group.log"))
        self.log_text = self.create_text_box()
        self.log_frame.layout().addWidget(self.log_text)
        content_layout.addWidget(self.log_frame, 1, 0)

        self.right_side_panel = QWidget()
        self.right_side_panel.setMinimumWidth(300)
        self.right_side_layout = QVBoxLayout(self.right_side_panel)
        self.right_side_layout.setContentsMargins(0, 0, 0, 0)
        self.right_side_layout.setSpacing(8)

        self.preview_frame = self.create_group_box(self.tr("group.preview"))
        self.preview_label = QLabel(self.tr("preview.none"))
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(260, 150)
        self.preview_frame.layout().addWidget(self.preview_label)

        self.answer_history_frame = self.create_group_box(self.tr("group.history"))
        self.answer_history_list = QListWidget()
        self.answer_history_list.setAlternatingRowColors(False)
        self.answer_history_list.setWordWrap(True)
        self.answer_history_frame.layout().addWidget(self.answer_history_list)

        self.right_side_layout.addWidget(self.preview_frame)
        self.right_side_layout.addWidget(self.answer_history_frame, stretch=1)
        content_layout.addWidget(self.right_side_panel, 0, 1, 2, 1)

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.addPermanentWidget(self.create_signature_label())
        self.setStatusBar(self.status_bar)

    def change_language(self) -> None:
        language = normalized_language(str(self.language_combo.currentData()))
        if language == self.language:
            return

        self.language = language
        self.settings.language = language
        save_language(language)
        self.apply_language()
        self.event_log.info("language.changed", language=language)
        self.set_status(self.tr("status.language_changed", language=language_label(language)))

    def apply_language(self) -> None:
        self.setWindowTitle(self.tr("window.main.title"))
        self.warning_label.setText(self.tr("warning.main"))
        self.provider_label.setText(self.llm_provider_summary())
        for text_key, button in self.toolbar_buttons.items():
            button.setText(self.tr(text_key))

        self.language_label.setText(self.tr("language.label"))
        combo_index = language_index(self.language)
        if self.language_combo.currentIndex() != combo_index:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(combo_index)
            self.language_combo.blockSignals(False)

        self.question_frame.setTitle(self.tr("group.question"))
        self.answer_frame.setTitle(self.tr("group.answer"))
        self.log_frame.setTitle(self.tr("group.log"))
        self.preview_frame.setTitle(self.tr("group.preview"))
        self.answer_history_frame.setTitle(self.tr("group.history"))
        if self.preview_label.pixmap() is None:
            self.preview_label.setText(self.tr("preview.none"))

    @staticmethod
    def qt_slot(callback: Callable) -> Callable:
        def wrapper(*_args: object) -> None:
            try:
                callback()
            except Exception as exc:
                owner = getattr(callback, "__self__", None)
                callback_name = getattr(callback, "__name__", repr(callback))
                if owner is not None and hasattr(owner, "event_log"):
                    owner.event_log.exception(
                        "ui.callback.error",
                        exc,
                        callback=callback_name,
                    )
                if owner is not None and hasattr(owner, "set_status"):
                    owner.set_status(f"{callback_name} failed: {exc}")
                else:
                    raise

        return wrapper

    @staticmethod
    def create_group_box(title: str) -> QGroupBox:
        group_box = QGroupBox(title)
        layout = QVBoxLayout(group_box)
        layout.setContentsMargins(6, 8, 6, 6)
        layout.setSpacing(0)
        return group_box

    @staticmethod
    def create_text_box() -> QTextEdit:
        text_box = QTextEdit()
        text_box.setAcceptRichText(False)
        text_box.setLineWrapMode(QTextEdit.WidgetWidth)
        text_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        text_box.setFont(QFont("Consolas", 9))
        return text_box

    @staticmethod
    def create_signature_label() -> QLabel:
        label = QLabel(APP_FOOTER_SIGNATURE)
        label.setStyleSheet("QLabel { color: #003300; font-family: Consolas; padding: 0 4px; }")
        return label

    def set_status(self, message: str) -> None:
        known_prefixes = ("Status:", "Estado:")
        if not message.startswith(known_prefixes):
            message = f"{self.tr('status.prefix')}: {message}"
        self.status_bar.showMessage(message)

    def enqueue_status(self, message: str) -> None:
        self.ui_queue.put(("status", message))

    def select_capture_window(self) -> None:
        self.clear_remote_sync_capture()
        self.event_log.info("capture_window.select.opened")
        try:
            exclude_hwnds = {int(self.winId())}
            if self.capture_box is not None:
                exclude_hwnds.add(int(self.capture_box.winId()))
            dialog = WindowPickerDialog(
                self.window_capture,
                exclude_hwnds,
                self,
                language=self.language,
            )
        except Exception as exc:
            self.event_log.exception("capture_window.select.unavailable", exc)
            QMessageBox.warning(self, self.tr("dialog.window_capture_unavailable"), str(exc))
            self.set_status(f"window capture unavailable: {exc}")
            return

        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.selected_window is None:
            self.event_log.info("capture_window.select.cancelled")
            return

        if self.capture_box is not None:
            self.capture_box.close()

        with self.capture_window_lock:
            self.selected_capture_window = dialog.selected_window

        self.event_log.info(
            "capture_window.selected",
            hwnd=dialog.selected_window.hwnd,
            title=dialog.selected_window.title,
            width=dialog.selected_window.width,
            height=dialog.selected_window.height,
            process_id=dialog.selected_window.process_id,
        )
        self.set_status(f"capturing selected window: {dialog.selected_window.title}")
        self.refresh_preview_async()

    def show_capture_box(self) -> None:
        self.clear_remote_sync_capture()
        self.clear_selected_capture_window()
        if self.capture_box is None:
            self.capture_box = CaptureBoxWindow(self.active_capture_region)
            self.capture_box.region_changed.connect(self.set_active_capture_region)
            self.capture_box.closed.connect(self.handle_capture_box_closed)

        self.capture_box.show()
        self.capture_box.raise_()
        self.set_active_capture_region(self.capture_box.capture_region())
        self.event_log.info(
            "capture_box.shown",
            region=self.current_capture_region().model_dump(),
            capture_running=self.is_capture_running(),
        )
        self.set_status("OCR box visible; capture uses the inside of the box")
        self.refresh_preview_async()

    def handle_capture_box_closed(self) -> None:
        self.capture_box = None
        self.set_active_capture_region(self.settings.region)
        self.event_log.info("capture_box.closed", fallback_region=self.settings.region.model_dump())
        if self.current_capture_window() is None and self.remote_sync_capture is None:
            self.set_status("OCR box closed; using config.json capture region")

    def set_active_capture_region(self, region: RegionSettings) -> None:
        with self.capture_region_lock:
            self.active_capture_region = region.model_copy()

    def current_capture_region(self) -> RegionSettings:
        with self.capture_region_lock:
            return self.active_capture_region.model_copy()

    def clear_selected_capture_window(self) -> None:
        with self.capture_window_lock:
            previous = self.selected_capture_window
            self.selected_capture_window = None
        if previous is not None:
            self.event_log.info(
                "capture_window.cleared",
                hwnd=previous.hwnd,
                title=previous.title,
            )

    def current_capture_window(self) -> WindowInfo | None:
        with self.capture_window_lock:
            return self.selected_capture_window

    def sync_ocr(self) -> None:
        self.event_log.info("sync_ocr.dialog.opened")
        dialog = SyncOcrDialog(self, language=self.language)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.event_log.info("sync_ocr.dialog.cancelled")
            return

        try:
            connection_info = parse_sync_details(dialog.sync_details())
        except ValueError as exc:
            self.event_log.warning("sync_ocr.details.invalid", error=str(exc))
            QMessageBox.warning(self, self.tr("dialog.sync.invalid_title"), str(exc))
            self.set_status(f"Sync OCR details invalid: {exc}")
            return

        remote_capture = RemoteSyncScreenCapture(connection_info)
        self.set_status("testing Sync OCR connection")
        try:
            remote_capture.test_connection()
        except Exception as exc:
            self.event_log.exception(
                "sync_ocr.connection.error",
                exc,
                host=connection_info.host,
                port=connection_info.port,
            )
            QMessageBox.warning(self, self.tr("dialog.sync.failed_title"), str(exc))
            self.set_status(f"Sync OCR connection failed: {exc}")
            return

        self.set_remote_sync_capture(remote_capture)
        self.event_log.info(
            "sync_ocr.connected",
            host=connection_info.host,
            port=connection_info.port,
        )
        self.set_status("Sync OCR connected; capture starting")
        self.refresh_preview_async()
        self.start_capture()

    def show_support(self) -> None:
        self.event_log.info("support.dialog.opened")
        show_support_dialog(self, self.language)

    def set_remote_sync_capture(self, remote_capture: RemoteSyncScreenCapture) -> None:
        self.clear_selected_capture_window()
        if self.capture_box is not None:
            self.capture_box.close()
            self.capture_box = None
        self.remote_sync_capture = remote_capture

    def clear_remote_sync_capture(self) -> None:
        if self.remote_sync_capture is None:
            return

        connection_info = self.remote_sync_capture.connection_info
        self.remote_sync_capture = None
        self.event_log.info(
            "sync_ocr.cleared",
            host=connection_info.host,
            port=connection_info.port,
        )

    def capture_mode(self) -> str:
        if self.remote_sync_capture is not None:
            return "sync_ocr"
        if self.current_capture_window() is not None:
            return "window"
        if self.capture_box is not None:
            return "ocr_box"
        return "config_region"

    def is_capture_running(self) -> bool:
        return bool(self.ocr_thread and self.ocr_thread.is_alive())

    def capture_ocr_image(self) -> Image.Image:
        if self.remote_sync_capture is not None:
            return self.remote_sync_capture.capture_region_image(self.current_capture_region())

        selected_window = self.current_capture_window()
        if selected_window is not None:
            return self.window_capture.capture_window_image(selected_window.hwnd)

        return self.screen_capture.capture_region_image(self.current_capture_region())

    def capture_ocr_text(self) -> str:
        image = self.capture_ocr_image()
        self.ui_queue.put(("preview_image", image.copy()))
        return self.ocr_engine.image_to_text(image, lang=self.settings.ocr_lang)

    def refresh_preview_async(self) -> None:
        threading.Thread(
            target=self.preview_worker,
            name="Gwisp-Preview",
            daemon=True,
        ).start()

    def preview_worker(self) -> None:
        try:
            self.ui_queue.put(("preview_image", self.capture_ocr_image()))
        except Exception as exc:
            self.event_log.exception(
                "preview.capture.error",
                exc,
                capture_mode=self.capture_mode(),
            )
            self.enqueue_status(f"preview capture error: {exc}")

    def connect_remote(self) -> None:
        command = self.settings.connect_command.strip()
        delay_ms = int(max(0.0, self.settings.connect_start_delay_seconds) * 1000)
        self.event_log.info(
            "connect.requested",
            has_command=bool(command),
            delay_ms=delay_ms,
        )

        if command:
            try:
                command_argv = parse_connect_command(command)
                subprocess.Popen(  # nosec B603
                    command_argv,
                    cwd=str(APP_DIR),
                    shell=False,
                )
            except Exception as exc:
                self.event_log.exception("connect.command.error", exc, has_command=True)
                self.set_status(f"connection command failed: {exc}")
                return

            self.event_log.info(
                "connect.command.launched",
                executable_name=command_argv[0].replace("\\", "/").rsplit("/", 1)[-1]
                if command_argv
                else "",
                arg_count=max(len(command_argv) - 1, 0),
            )
            self.set_status("connection command launched; capture will start automatically")
            QTimer.singleShot(delay_ms, self.start_capture)
            return

        self.event_log.info("connect.no_command_starting_capture")
        self.set_status("connect command is empty; open the Ubuntu remote window now")
        self.start_capture()

    def start_capture(self) -> None:
        self.event_log.info(
            "capture.start.requested",
            capture_mode=self.capture_mode(),
            llm_ready=self.llm_ready,
        )
        if self.ocr_thread and self.ocr_thread.is_alive():
            self.event_log.warning("capture.start.ignored_already_running")
            self.set_status("capture is already running")
            return

        if self.settings.llm_auto_warmup and not self.llm_ready:
            self.event_log.info("capture.start.waiting_for_llm_warmup")
            self.load_ai_model(auto_start=True)
            return

        self.start_capture_now()

    def start_capture_now(self) -> None:
        self.stop_event.clear()
        self.ocr_thread = threading.Thread(
            target=self.ocr_loop,
            name="Gwisp-OCR",
            daemon=True,
        )
        self.ocr_thread.start()
        self.event_log.info("capture.started", capture_mode=self.capture_mode())
        self.set_status("capture running")

    def pause_capture(self) -> None:
        self.stop_event.set()
        self.event_log.info("capture.pause.requested", was_running=self.is_capture_running())
        self.set_status("capture paused")

    def clear_views(self) -> None:
        self.question_text.clear()
        self.answer_text.clear()
        self.log_text.clear()
        self.answer_history_list.clear()
        self.log_store.clear()
        self.pipeline.reset_history()
        self.event_log.info("views.cleared", duplicate_history_reset=True)
        self.set_status("views and duplicate history cleared")

    def save_log_now(self) -> None:
        self.log_store.write()
        self.event_log.info("qa_log.saved", output_log_path=self.output_log_path)
        self.set_status(f"log saved to {self.output_log_path}")

    def test_ocr_once(self) -> None:
        self.event_log.info("ocr.test_once.requested", capture_mode=self.capture_mode())
        threading.Thread(
            target=self.test_ocr_worker,
            name="Gwisp-TestOCR",
            daemon=True,
        ).start()

    def check_setup(self) -> None:
        self.event_log.info("setup_check.requested")
        self.set_status("checking setup")
        self.replace_text(self.answer_text, "Checking Gwisp setup...")
        threading.Thread(
            target=self.check_setup_worker,
            name="Gwisp-SetupCheck",
            daemon=True,
        ).start()

    def check_setup_worker(self) -> None:
        lines = ["Gwisp setup check", ""]
        ok = True

        if self.tesseract_path and self.tesseract_path.exists():
            lines.append(f"[OK] Tesseract: {self.tesseract_path}")
            try:
                lines.append(f"[OK] Tesseract version: {self.ocr_engine.version_line()}")
            except Exception as exc:
                ok = False
                lines.append(f"[FAIL] Tesseract did not run: {exc}")

            try:
                available_langs = self.ocr_engine.available_languages()
                requested_langs = {
                    item.strip() for item in self.settings.ocr_lang.split("+") if item.strip()
                }
                missing_langs = sorted(requested_langs - available_langs)
                if missing_langs:
                    ok = False
                    lines.append(f"[FAIL] Missing OCR languages: {', '.join(missing_langs)}")
                else:
                    lines.append(f"[OK] OCR languages: {self.settings.ocr_lang}")
            except Exception as exc:
                ok = False
                lines.append(f"[FAIL] Could not list OCR languages: {exc}")
        else:
            ok = False
            lines.append(
                "[FAIL] Tesseract not found. Install it or enable/use a valid tesseract_cmd."
            )

        lines.append("")
        lines.append(f"[OK] AI provider: {self.llm_provider_name()}")
        lines.append(f"[OK] AI model: {self.llm_model_name()}")

        if getattr(self.llm_client, "provider_name", "") == "ollama":
            try:
                models = self.llm_client.installed_models()
                model_name = self.llm_model_name()
                lines.append(f"[OK] Ollama API: {self.llm_client.tags_url}")
                if model_name in models:
                    lines.append(f"[OK] Ollama model installed: {model_name}")
                else:
                    ok = False
                    available = ", ".join(sorted(models)) or "(none)"
                    lines.append(f"[FAIL] Ollama model missing: {model_name}")
                    lines.append(f"       Available models: {available}")
                    lines.append(f"       Run: ollama pull {model_name}")
            except Exception as exc:
                ok = False
                lines.append(f"[FAIL] Ollama API is not reachable: {exc}")
        else:
            if self.settings.cloud_api_url.strip():
                lines.append(f"[OK] Cloud API endpoint: {self.settings.cloud_api_url}")
            else:
                ok = False
                lines.append("[FAIL] Cloud API endpoint is empty: set cloud_api_url")

            if self.settings.cloud_api_key.strip():
                lines.append("[OK] Cloud API key configured")
            else:
                ok = False
                lines.append("[FAIL] Cloud API key missing: set GWISP_CLOUD_API_KEY")

        lines.append("")
        lines.append("Result: OK" if ok else "Result: action needed")
        self.event_log.info("setup_check.finished", success=ok)
        self.ui_queue.put(("setup_report", "\n".join(lines), ok))

    def load_ai_model(self, auto_start: bool = False) -> None:
        if not self.try_begin_processing():
            self.event_log.warning(
                "llm.warmup.ignored_busy",
                auto_start=auto_start,
            )
            self.set_status("AI provider is already busy; load request ignored")
            return

        model_name = self.llm_model_name()
        provider_name = self.llm_provider_name()
        self.event_log.info(
            "llm.warmup.started",
            provider=provider_name,
            model=model_name,
            auto_start=auto_start,
        )
        self.set_status(f"loading {provider_name} model {model_name}")
        self.replace_text(
            self.answer_text,
            f"Loading {provider_name} model: {model_name}\n\nPlease wait...",
        )
        threading.Thread(
            target=self.llm_warmup_worker,
            args=(auto_start,),
            name="Gwisp-LlmWarmup",
            daemon=True,
        ).start()

    def test_ai_provider(self) -> None:
        test_question = (
            "Authorized practice quiz. Which option is correct?\n"
            "A) 2 + 2 = 5\n"
            "B) 2 + 2 = 4\n"
            "C) 2 + 2 = 6\n"
            "Return the correct alternative first."
        )
        if not self.try_begin_processing():
            self.event_log.warning("llm.test.ignored_busy")
            self.set_status("AI provider is still responding; test ignored")
            return

        self.event_log.info(
            "llm.test.started",
            provider=self.llm_provider_name(),
            model=self.llm_model_name(),
        )
        self.set_status("testing AI provider")
        self.replace_text(self.answer_text, f"Testing {self.llm_provider_name()}...")
        threading.Thread(
            target=self.llm_worker,
            args=(test_question, datetime.datetime.now(), True),
            name="Gwisp-TestLlm",
            daemon=True,
        ).start()

    def llm_warmup_worker(self, auto_start: bool) -> None:
        try:
            status = self.llm_client.warm_up()
            success = True
            self.llm_ready = True
            self.event_log.info("llm.warmup.finished", success=True, auto_start=auto_start)
        except Exception as exc:
            status = f"{self.llm_provider_name()} load failed: {exc}"
            success = False
            self.llm_ready = False
            self.event_log.exception(
                "llm.warmup.error",
                exc,
                auto_start=auto_start,
            )
        finally:
            self.end_processing()

        self.ui_queue.put(("llm_ready", success, status, auto_start))

    def ocr_loop(self) -> None:
        self.event_log.info(
            "capture.thread.started", interval_seconds=self.settings.interval_seconds
        )
        self.enqueue_status("capture thread started")
        interval = max(0.2, self.settings.interval_seconds)

        while not self.stop_event.is_set():
            try:
                raw_text = self.capture_ocr_text()
                self.handle_ocr_result(raw_text, datetime.datetime.now())
            except Exception as exc:
                self.event_log.exception(
                    "ocr.capture.error",
                    exc,
                    capture_mode=self.capture_mode(),
                )
                self.enqueue_status(f"OCR error: {exc}")

            self.stop_event.wait(interval)

        self.event_log.info("capture.thread.stopped")
        self.enqueue_status("capture thread stopped")

    def test_ocr_worker(self) -> None:
        self.enqueue_status("running one OCR capture")
        try:
            raw_text = self.capture_ocr_text()
            cleaned = clean_ocr_text(raw_text)
            self.ui_queue.put(("question", cleaned or "(No OCR text detected.)"))

            if not cleaned or compact_length(cleaned) < self.settings.min_chars:
                self.enqueue_status("OCR test finished; text is empty or shorter than min_chars")
            elif looks_like_app_window(cleaned):
                self.enqueue_status(APP_WINDOW_STATUS)
            else:
                self.enqueue_status("OCR test finished")
            self.event_log.info(
                "ocr.test_once.finished",
                raw_length=len(raw_text),
                cleaned_length=len(cleaned),
            )
        except Exception as exc:
            self.event_log.exception(
                "ocr.test_once.error",
                exc,
                capture_mode=self.capture_mode(),
            )
            self.enqueue_status(f"OCR test error: {exc}")

    def handle_ocr_result(self, raw_text: str, captured_at: datetime.datetime) -> None:
        decision = self.pipeline.prepare_question(raw_text)
        if not decision.accepted:
            self.event_log.info(
                "ocr.question.ignored",
                status=decision.status,
                message=decision.message,
                raw_length=len(raw_text),
                cleaned_length=len(decision.question),
            )
            self.enqueue_status(decision.message)
            return

        question = decision.question
        if not self.try_begin_processing():
            self.event_log.warning(
                "ocr.question.ignored_llm_busy",
                raw_length=len(raw_text),
                cleaned_length=len(question),
            )
            self.enqueue_status("AI provider is still responding; new OCR text ignored")
            return

        self.pipeline.remember_question(question)
        self.event_log.info(
            "ocr.question.accepted",
            cleaned_length=len(question),
            captured_at=captured_at.isoformat(timespec="seconds"),
        )
        self.ui_queue.put(("question", question))
        self.ui_queue.put(("answer", f"Waiting for {self.llm_provider_name()} response..."))
        self.enqueue_status(decision.message)

        threading.Thread(
            target=self.llm_worker,
            args=(question, captured_at, False),
            name="Gwisp-Llm",
            daemon=True,
        ).start()

    def try_begin_processing(self) -> bool:
        with self.processing_lock:
            if self.processing:
                return False
            self.processing = True
            return True

    def end_processing(self) -> None:
        with self.processing_lock:
            self.processing = False

    def llm_worker(self, question: str, captured_at: datetime.datetime, is_test: bool) -> None:
        try:
            answer, captured_at = self.pipeline.answer_question(question, captured_at)
            if not answer.startswith("("):
                self.llm_ready = True
            self.event_log.info(
                "llm.answer.finished",
                is_test=is_test,
                provider=self.llm_provider_name(),
                question_length=len(question),
                answer_length=len(answer),
            )
        except Exception as exc:
            answer = f"{self.llm_provider_name()} error: {exc}"
            self.llm_ready = False
            self.event_log.exception(
                "llm.answer.error",
                exc,
                is_test=is_test,
                question_length=len(question),
            )
        finally:
            self.end_processing()

        event_name = "test_answer" if is_test else "final_answer"
        self.ui_queue.put((event_name, question, answer, captured_at))

    def drain_ui_queue(self) -> None:
        try:
            while True:
                event = self.ui_queue.get_nowait()
                try:
                    self.handle_ui_event(event)
                except Exception as exc:
                    self.event_log.exception(
                        "ui.queue_event.error",
                        exc,
                        event_type=event[0] if event else "(empty)",
                    )
                    self.set_status(f"UI event failed: {exc}")
        except queue.Empty:
            pass

    def handle_ui_event(self, event: tuple) -> None:
        event_type = event[0]

        if event_type == "status":
            self.set_status(event[1])
        elif event_type == "question":
            self.replace_text(self.question_text, event[1])
        elif event_type == "answer":
            self.replace_text(self.answer_text, event[1])
        elif event_type == "preview_image":
            self.set_preview_image(event[1])
        elif event_type == "setup_report":
            _, report, success = event
            self.replace_text(self.answer_text, report)
            self.set_status("setup check OK" if success else "setup check found issues")
        elif event_type == "llm_ready":
            _, success, status, auto_start = event
            self.replace_text(self.answer_text, status)
            self.set_status(status)
            if success and auto_start:
                self.start_capture_now()
        elif event_type == "final_answer":
            _, question, answer, captured_at = event
            self.replace_text(self.answer_text, answer)
            self.add_answer_history_entry(answer)
            self.add_log_entry(captured_at, question, answer)
            self.set_status("AI response received")
        elif event_type == "test_answer":
            _, _question, answer, _captured_at = event
            self.replace_text(self.answer_text, answer)
            self.set_status("AI test finished")

    @staticmethod
    def replace_text(widget: QTextEdit, value: str) -> None:
        widget.setPlainText(value)
        cursor = widget.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        widget.setTextCursor(cursor)

    @staticmethod
    def pil_image_to_pixmap(image: Image.Image) -> QPixmap:
        rgb_image = image.convert("RGB")
        width, height = rgb_image.size
        image_data = rgb_image.tobytes("raw", "RGB")
        qimage = QImage(
            image_data,
            width,
            height,
            width * 3,
            QImage.Format.Format_RGB888,
        ).copy()
        return QPixmap.fromImage(qimage)

    def set_preview_image(self, image: Image.Image) -> None:
        pixmap = self.pil_image_to_pixmap(image)
        scaled = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def add_answer_history_entry(self, answer: str) -> None:
        entry = parse_answer_history_entry(answer)
        if entry is None:
            self.event_log.info("answer_history.skipped", reason="recapture_or_empty")
            return

        number = self.answer_history_list.count() + 1
        item = QListWidgetItem(f"{number} - {entry.summary}")
        widget = AnswerHistoryWidget(number, entry, lambda: item.setSizeHint(widget.sizeHint()))
        item.setSizeHint(widget.sizeHint())
        self.answer_history_list.addItem(item)
        self.answer_history_list.setItemWidget(item, widget)
        self.answer_history_list.scrollToBottom()

    def add_log_entry(self, captured_at: datetime.datetime, question: str, answer: str) -> None:
        entry = self.log_store.add(captured_at, question, answer)
        self.log_text.moveCursor(self.log_text.textCursor().MoveOperation.End)
        self.log_text.insertPlainText(entry + "\n")
        self.log_text.moveCursor(self.log_text.textCursor().MoveOperation.End)

    def write_log_file(self) -> None:
        self.log_store.write()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.stop_event.set()
        self.event_log.info("app.closing", capture_running=self.is_capture_running())
        if self.capture_box is not None:
            self.capture_box.close()
        super().closeEvent(event)


def main() -> None:
    configure_windows_app_id()
    app = QApplication.instance() or QApplication([])
    apply_app_icon(app)
    window = GwispWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
