from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LANGUAGE = "en"


@dataclass(frozen=True)
class LanguageOption:
    code: str
    flag: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.flag} {self.name}"


SUPPORTED_LANGUAGES = (
    LanguageOption("en", "🏴", "English"),
    LanguageOption("pt", "🇧🇷", "Português"),
    LanguageOption("de", "🇩🇪", "Deutsch"),
)
SUPPORTED_LANGUAGE_CODES = {language.code for language in SUPPORTED_LANGUAGES}

TRANSLATIONS = {
    "en": {
        "language.label": "Language",
        "window.main.title": "Gwisp - Alpha build 1.0.3",
        "window.sync.title": "Gwisp Sync OCR - Alpha build 1.0.3",
        "warning.main": (
            "Use OCR box over the source question. Keep this window open for answers "
            "from the selected AI provider."
        ),
        "warning.sync": (
            "Click Sync OCR, then paste the shown details into Gwisp on the first machine."
        ),
        "button.connect_remote": "Connect",
        "button.select_capture_window": "Select capture window",
        "button.sync_ocr": "Sync OCR",
        "button.ocr_box": "OCR box",
        "button.start": "Start",
        "button.pause": "Pause",
        "button.clear": "Clear",
        "button.save_log_now": "Save log now",
        "button.test_ocr_once": "Test OCR once",
        "button.check_setup": "Check setup",
        "button.load_model": "Load model",
        "button.test_ai_provider": "Test AI",
        "llm.provider": "AI provider: {provider} ({model})",
        "button.support": "Support",
        "group.question": "Question obtained by OCR",
        "group.answer": "AI answer",
        "group.log": "Real-time Q&A log",
        "group.preview": "Capture preview",
        "group.history": "Previous answers",
        "group.sync_details": "Sync OCR details",
        "preview.none": "No preview",
        "dialog.window_picker.title": "Select capture window",
        "dialog.window_picker.refresh": "Refresh",
        "dialog.sync.title": "Sync OCR",
        "dialog.sync.instructions": (
            "Paste the Host, Port and Token shown on the second machine, then connect."
        ),
        "dialog.sync.connect": "Connect",
        "dialog.sync.invalid_title": "Invalid Sync OCR details",
        "dialog.sync.failed_title": "Sync OCR connection failed",
        "dialog.window_capture_unavailable": "Window capture unavailable",
        "status.prefix": "Status",
        "status.idle": "idle",
        "status.idle_bar": "Status: idle",
        "status.ready_tesseract": "ready; Tesseract: {path}",
        "status.language_changed": "language changed to {language}",
        "status.sync_connected": "Connected to Gwisp. Sync OCR is running.",
        "status.sync_connected_bar": "Status: connected",
        "status.sync_waiting": (
            "Please fill this on the first machine. Waiting for connection{dots}"
        ),
        "status.sync_waiting_bar": "Status: waiting for first machine",
        "support.title": "Support Gwisp",
        "support.intro": (
            "If Gwisp helps you, you can support the project with a crypto donation."
        ),
        "support.copy": "Copy",
        "support.verify": "Donation addresses only. Verify the address before sending funds.",
        "support.copied": "{currency} address copied.",
    },
    "pt": {
        "language.label": "Idioma",
        "window.main.title": "Gwisp - Alpha build 1.0.3",
        "window.sync.title": "Gwisp Sync OCR - Alpha build 1.0.3",
        "warning.main": (
            "Use a caixa OCR sobre a pergunta de origem. Mantenha esta janela aberta "
            "para respostas do provedor de IA selecionado."
        ),
        "warning.sync": (
            "Clique em Sync OCR e cole os detalhes mostrados no Gwisp da primeira maquina."
        ),
        "button.connect_remote": "Conectar",
        "button.select_capture_window": "Selecionar janela",
        "button.sync_ocr": "Sync OCR",
        "button.ocr_box": "Caixa OCR",
        "button.start": "Iniciar",
        "button.pause": "Pausar",
        "button.clear": "Limpar",
        "button.save_log_now": "Salvar log",
        "button.test_ocr_once": "Testar OCR",
        "button.check_setup": "Checar setup",
        "button.load_model": "Carregar modelo",
        "button.test_ai_provider": "Testar IA",
        "llm.provider": "Provedor de IA: {provider} ({model})",
        "button.support": "Apoiar",
        "group.question": "Pergunta obtida por OCR",
        "group.answer": "Resposta da IA",
        "group.log": "Log de Q&A em tempo real",
        "group.preview": "Previa da captura",
        "group.history": "Respostas anteriores",
        "group.sync_details": "Detalhes do Sync OCR",
        "preview.none": "Sem previa",
        "dialog.window_picker.title": "Selecionar janela de captura",
        "dialog.window_picker.refresh": "Atualizar",
        "dialog.sync.title": "Sync OCR",
        "dialog.sync.instructions": (
            "Cole o Host, a Porta e o Token mostrados na segunda maquina, depois conecte."
        ),
        "dialog.sync.connect": "Conectar",
        "dialog.sync.invalid_title": "Detalhes do Sync OCR invalidos",
        "dialog.sync.failed_title": "Conexao Sync OCR falhou",
        "dialog.window_capture_unavailable": "Captura de janela indisponivel",
        "status.prefix": "Estado",
        "status.idle": "ocioso",
        "status.idle_bar": "Estado: ocioso",
        "status.ready_tesseract": "pronto; Tesseract: {path}",
        "status.language_changed": "idioma alterado para {language}",
        "status.sync_connected": "Conectado ao Gwisp. Sync OCR esta rodando.",
        "status.sync_connected_bar": "Estado: conectado",
        "status.sync_waiting": "Preencha isso na primeira maquina. Aguardando conexao{dots}",
        "status.sync_waiting_bar": "Estado: aguardando primeira maquina",
        "support.title": "Apoiar o Gwisp",
        "support.intro": (
            "Se o Gwisp te ajuda, voce pode apoiar o projeto com uma doacao em cripto."
        ),
        "support.copy": "Copiar",
        "support.verify": "Enderecos apenas para doacao. Verifique o endereco antes de enviar.",
        "support.copied": "Endereco {currency} copiado.",
    },
    "de": {
        "language.label": "Sprache",
        "window.main.title": "Gwisp - Alpha build 1.0.3",
        "window.sync.title": "Gwisp Sync OCR - Alpha build 1.0.3",
        "warning.main": (
            "OCR-Feld ueber die Quellfrage legen. Dieses Fenster fuer Antworten "
            "des ausgewaehlten KI-Anbieters offen lassen."
        ),
        "warning.sync": (
            "Auf Sync OCR klicken und die Daten in Gwisp auf dem ersten Rechner einfuegen."
        ),
        "button.connect_remote": "Verbinden",
        "button.select_capture_window": "Fenster waehlen",
        "button.sync_ocr": "Sync OCR",
        "button.ocr_box": "OCR-Feld",
        "button.start": "Start",
        "button.pause": "Pause",
        "button.clear": "Leeren",
        "button.save_log_now": "Log speichern",
        "button.test_ocr_once": "OCR testen",
        "button.check_setup": "Setup pruefen",
        "button.load_model": "Modell laden",
        "button.test_ai_provider": "KI testen",
        "llm.provider": "KI-Anbieter: {provider} ({model})",
        "button.support": "Unterstuetzen",
        "group.question": "Per OCR erkannte Frage",
        "group.answer": "KI-Antwort",
        "group.log": "Q&A-Log in Echtzeit",
        "group.preview": "Capture-Vorschau",
        "group.history": "Vorherige Antworten",
        "group.sync_details": "Sync-OCR-Details",
        "preview.none": "Keine Vorschau",
        "dialog.window_picker.title": "Capture-Fenster waehlen",
        "dialog.window_picker.refresh": "Aktualisieren",
        "dialog.sync.title": "Sync OCR",
        "dialog.sync.instructions": (
            "Host, Port und Token vom zweiten Rechner einfuegen und dann verbinden."
        ),
        "dialog.sync.connect": "Verbinden",
        "dialog.sync.invalid_title": "Ungueltige Sync-OCR-Daten",
        "dialog.sync.failed_title": "Sync-OCR-Verbindung fehlgeschlagen",
        "dialog.window_capture_unavailable": "Fensteraufnahme nicht verfuegbar",
        "status.prefix": "Status",
        "status.idle": "bereit",
        "status.idle_bar": "Status: bereit",
        "status.ready_tesseract": "bereit; Tesseract: {path}",
        "status.language_changed": "Sprache geaendert zu {language}",
        "status.sync_connected": "Mit Gwisp verbunden. Sync OCR laeuft.",
        "status.sync_connected_bar": "Status: verbunden",
        "status.sync_waiting": "Bitte auf dem ersten Rechner eintragen. Warte auf Verbindung{dots}",
        "status.sync_waiting_bar": "Status: warte auf ersten Rechner",
        "support.title": "Gwisp unterstuetzen",
        "support.intro": (
            "Wenn Gwisp hilfreich ist, kannst du das Projekt mit einer Krypto-Spende unterstuetzen."
        ),
        "support.copy": "Kopieren",
        "support.verify": "Nur Spendenadressen. Adresse vor dem Senden pruefen.",
        "support.copied": "{currency}-Adresse kopiert.",
    },
}


def normalized_language(language_code: str | None) -> str:
    if not language_code:
        return DEFAULT_LANGUAGE

    code = language_code.strip().lower()
    return code if code in SUPPORTED_LANGUAGE_CODES else DEFAULT_LANGUAGE


def language_label(language_code: str | None) -> str:
    code = normalized_language(language_code)
    for option in SUPPORTED_LANGUAGES:
        if option.code == code:
            return option.label
    return SUPPORTED_LANGUAGES[0].label


def language_index(language_code: str | None) -> int:
    code = normalized_language(language_code)
    for index, option in enumerate(SUPPORTED_LANGUAGES):
        if option.code == code:
            return index
    return 0


def translate(language_code: str | None, key: str, **format_values: object) -> str:
    code = normalized_language(language_code)
    template = TRANSLATIONS.get(code, {}).get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if format_values:
        return template.format(**format_values)
    return template
