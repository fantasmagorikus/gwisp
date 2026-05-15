from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gwisp.i18n import normalized_language, translate
from gwisp.support import SUPPORT_ADDRESSES


class SupportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, language: str = "en") -> None:
        super().__init__(parent)
        self.language = normalized_language(language)
        self.setWindowTitle(self.tr("support.title"))
        self.setMinimumWidth(680)
        if parent is not None and not parent.windowIcon().isNull():
            self.setWindowIcon(parent.windowIcon())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        intro = QLabel(self.tr("support.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        address_grid = QGridLayout()
        address_grid.setContentsMargins(0, 4, 0, 4)
        address_grid.setHorizontalSpacing(8)
        address_grid.setVerticalSpacing(6)
        layout.addLayout(address_grid)

        for row, (currency, address) in enumerate(SUPPORT_ADDRESSES.items()):
            currency_label = QLabel(currency)
            address_field = QLineEdit(address)
            address_field.setReadOnly(True)
            address_field.setMinimumWidth(470)
            copy_button = QPushButton(self.tr("support.copy"))
            copy_button.setFixedWidth(82)
            copy_button.clicked.connect(
                lambda _checked=False, value=address, name=currency: self.copy_address(value, name)
            )

            address_grid.addWidget(currency_label, row, 0)
            address_grid.addWidget(address_field, row, 1)
            address_grid.addWidget(copy_button, row, 2)

        self.status_label = QLabel(self.tr("support.verify"))
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def tr(self, key: str, **format_values: object) -> str:
        return translate(self.language, key, **format_values)

    def copy_address(self, address: str, currency: str) -> None:
        QApplication.clipboard().setText(address)
        self.status_label.setText(self.tr("support.copied", currency=currency))


def show_support_dialog(parent: QWidget, language: str) -> None:
    dialog = SupportDialog(parent=parent, language=language)
    dialog.exec()
