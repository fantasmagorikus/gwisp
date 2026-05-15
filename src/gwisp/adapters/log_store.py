import datetime as dt
from pathlib import Path


def format_log_entry(captured_at: dt.datetime, question: str, answer: str) -> str:
    timestamp = captured_at.strftime("%Y-%m-%d %H:%M:%S")
    return (
        "============================================================\n"
        f"CAPTURED AT: {timestamp}\n"
        "============================================================\n"
        "QUESTION:\n"
        f"{question.strip()}\n"
        "ANSWER:\n"
        f"{answer.strip()}\n"
    )


class FileLogStore:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.entries: list[str] = []

    def clear(self) -> None:
        self.entries.clear()

    def add(self, captured_at: dt.datetime, question: str, answer: str) -> str:
        entry = format_log_entry(captured_at, question, answer)
        self.entries.append(entry)
        self.write()
        return entry

    def write(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(self.entries)
        if content:
            content += "\n"
        self.output_path.write_text(content, encoding="utf-8")
