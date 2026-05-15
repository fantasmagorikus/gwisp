from gwisp.i18n import language_index, language_label, normalized_language, translate


def test_language_helpers_fallback_to_english() -> None:
    assert normalized_language("unknown") == "en"
    assert language_index("unknown") == 0
    assert language_label("unknown") == "🏴 English"


def test_translate_accepts_language_format_placeholder() -> None:
    message = translate("pt", "status.language_changed", language="🇧🇷 Português")

    assert message == "idioma alterado para 🇧🇷 Português"
