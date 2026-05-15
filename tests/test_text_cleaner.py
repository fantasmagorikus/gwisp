from gwisp.services.text_cleaner import (
    clean_ocr_text,
    compact_length,
    comparable_text,
    looks_like_app_window,
)


def test_clean_ocr_text_removes_noise_and_keeps_question() -> None:
    raw = "\x00====\nWhich option is correct???!!!!\nA) Alpha\n||||||||\nB) Beta"

    cleaned = clean_ocr_text(raw)

    assert "Which option is correct?" in cleaned
    assert "A) Alpha" in cleaned
    assert "B) Beta" in cleaned
    assert "||||" not in cleaned


def test_comparable_text_normalizes_for_duplicate_detection() -> None:
    assert comparable_text("  Olá,   Mundo!!! ") == "olá mundo"


def test_compact_length_ignores_whitespace() -> None:
    assert compact_length("a b\nc") == 3


def test_looks_like_app_window_detects_own_ui_text() -> None:
    assert looks_like_app_window("Gwisp\nQuestion obtained by OCR")
