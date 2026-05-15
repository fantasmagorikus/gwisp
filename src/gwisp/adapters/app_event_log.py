import datetime as dt
import json
import threading
from pathlib import Path
from typing import Any


class ApplicationEventLog:
    def __init__(
        self,
        output_path: Path,
        max_bytes: int = 1_000_000,
        backup_count: int = 3,
    ) -> None:
        self.output_path = output_path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.lock = threading.Lock()
        self.last_error: str | None = None

    def info(self, event: str, message: str = "", **context: Any) -> None:
        self.record("INFO", event, message, **context)

    def warning(self, event: str, message: str = "", **context: Any) -> None:
        self.record("WARNING", event, message, **context)

    def error(self, event: str, message: str = "", **context: Any) -> None:
        self.record("ERROR", event, message, **context)

    def exception(self, event: str, exc: Exception, message: str = "", **context: Any) -> None:
        context = {
            **context,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }
        self.record("ERROR", event, message, **context)

    def record(self, level: str, event: str, message: str = "", **context: Any) -> None:
        entry = {
            "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "level": level.upper(),
            "event": event,
            "message": message,
            "context": sanitize_context(context),
        }
        line = json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n"
        payload = line.encode("utf-8")

        try:
            with self.lock:
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                self.rotate_if_needed(len(payload))
                with self.output_path.open("ab") as log_file:
                    log_file.write(payload)
        except Exception as exc:
            self.last_error = str(exc)

    def rotate_if_needed(self, incoming_size: int) -> None:
        if self.max_bytes <= 0 or self.backup_count <= 0 or not self.output_path.exists():
            return

        current_size = self.output_path.stat().st_size
        if current_size + incoming_size <= self.max_bytes:
            return

        for index in range(self.backup_count, 0, -1):
            source = self.rotated_path(index)
            if not source.exists():
                continue

            if index == self.backup_count:
                source.unlink()
            else:
                source.replace(self.rotated_path(index + 1))

        self.output_path.replace(self.rotated_path(1))

    def rotated_path(self, index: int) -> Path:
        return self.output_path.with_name(f"{self.output_path.name}.{index}")


def sanitize_context(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): sanitize_context(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [sanitize_context(item) for item in value]
    return str(value)
