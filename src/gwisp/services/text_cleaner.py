import re

APP_WINDOW_STATUS = "App window detected inside OCR region. Move the app or adjust capture region."

APP_LOOP_STRONG_MARKERS = [
    "gwisp",
    "question obtained by ocr",
    "ai answer",
    "real-time q&a log",
    "captured at",
    "question:",
    "answer:",
    "status:",
    "save log now",
    "test ocr once",
    "test ai",
    "check setup",
    "load model",
    "conectar",
]

APP_LOOP_BUTTON_LINES = {"start", "pause", "clear", "check setup", "load model", "conectar"}


def clean_ocr_text(raw_text: str) -> str:
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    raw_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", raw_text)
    raw_text = re.sub(r"[|]{3,}", " ", raw_text)
    raw_text = re.sub(r"[._\-=\u2014]{5,}", " ", raw_text)

    cleaned_lines = []
    for line in raw_text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = re.sub(r"([^\w\s])\1{3,}", r"\1", line)

        if not line or not re.search(r"[A-Za-z\u00c0-\u00ff0-9]", line):
            continue

        compact = re.sub(r"\s+", "", line)
        alnum_count = sum(char.isalnum() for char in compact)
        if compact and alnum_count / len(compact) < 0.35:
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def comparable_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9\u00e0-\u00ff: &+\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def looks_like_app_window(text: str) -> bool:
    normalized = comparable_text(text)
    if any(marker in normalized for marker in APP_LOOP_STRONG_MARKERS):
        return True

    normalized_lines = {comparable_text(line) for line in text.splitlines()}
    return bool(normalized_lines & APP_LOOP_BUTTON_LINES)
