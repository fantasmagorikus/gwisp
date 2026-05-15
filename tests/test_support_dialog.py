import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gwisp.support import BTC_ADDRESS, MONERO_ADDRESS, SUPPORT_ADDRESSES
from gwisp.ui.support_dialog import SupportDialog


def test_support_addresses_are_exact_and_trimmed() -> None:
    assert BTC_ADDRESS == "bc1qfnlslkc9lm7327d8ruz6us6rs25299fx752h4j"
    assert MONERO_ADDRESS == (
        "46qeT3qhJgfYditXfaSqM1enNAottE26EQczmtNbiT57iJzFRHxuBjQN3jdtM8FPwFMRt"
        "QYWc9CSXBYLT7RhBaHcBfDvwrE"
    )
    assert all(value == value.strip() for value in SUPPORT_ADDRESSES.values())


def test_support_dialog_copies_address_to_clipboard() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = SupportDialog(language="pt")

    try:
        dialog.copy_address(BTC_ADDRESS, "Bitcoin (BTC)")

        assert app.clipboard().text() == BTC_ADDRESS
        assert dialog.status_label.text() == "Endereco Bitcoin (BTC) copiado."
    finally:
        dialog.close()
