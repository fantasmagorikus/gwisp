import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_TITLE = "Gwisp"
APP_VERSION = "1.0.3"
APP_VERSION_LABEL = "Alpha build 1.0.3"
APP_SIGNATURE = "> developed by @fantasmagorikus"
APP_FOOTER_SIGNATURE = f"{APP_VERSION_LABEL} | {APP_SIGNATURE}"


def resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    argv_path = Path(sys.argv[0]).resolve()
    if argv_path.exists():
        candidate = argv_path.parent
        if (candidate / "config.json").exists() or (candidate / ".tools").exists():
            return candidate

    return Path.cwd()


APP_DIR = resolve_app_dir()
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "language": "en",
    "region": {"left": 200, "top": 150, "width": 1100, "height": 650},
    "interval_seconds": 1.5,
    "min_chars": 15,
    "duplicate_threshold": 0.92,
    "ocr_lang": "eng+por",
    "tesseract_cmd": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "tesseract_auto_detect": True,
    "ollama_url": "http://localhost:11434/api/generate",
    "ollama_model": "gemma4:e4b",
    "ollama_num_gpu": 32,
    "ollama_num_ctx": 2048,
    "ollama_num_predict": 100,
    "ollama_temperature": 0.1,
    "ollama_auto_warmup": True,
    "ollama_keep_alive": "30m",
    "ollama_connect_timeout_seconds": 10,
    "ollama_request_timeout_seconds": 240,
    "always_on_top": True,
    "output_log_file": "gwisp_log.txt",
    "event_log_file": "logs/gwisp_events.log",
    "connect_command": "",
    "connect_start_delay_seconds": 3.0,
}


class RegionSettings(BaseModel):
    left: int = Field(default=200, ge=0)
    top: int = Field(default=150, ge=0)
    width: int = Field(default=1100, gt=0)
    height: int = Field(default=650, gt=0)

    def as_mss_region(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GWISP_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    language: str = "en"
    region: RegionSettings = Field(default_factory=RegionSettings)
    interval_seconds: float = Field(default=1.5, gt=0)
    min_chars: int = Field(default=15, ge=0)
    duplicate_threshold: float = Field(default=0.92, ge=0, le=1)
    ocr_lang: str = "eng+por"
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    tesseract_auto_detect: bool = True
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "gemma4:e4b"
    ollama_num_gpu: int = Field(default=32, ge=0)
    ollama_num_ctx: int = Field(default=2048, gt=0)
    ollama_num_predict: int = Field(default=100, gt=0)
    ollama_temperature: float = Field(default=0.1, ge=0)
    ollama_auto_warmup: bool = True
    ollama_keep_alive: str = "30m"
    ollama_connect_timeout_seconds: float = Field(default=10, gt=0)
    ollama_request_timeout_seconds: float = Field(default=240, gt=0)
    always_on_top: bool = True
    output_log_file: str = "gwisp_log.txt"
    event_log_file: str = "logs/gwisp_events.log"
    connect_command: str = ""
    connect_start_delay_seconds: float = Field(default=3.0, ge=0)

    def resolve_output_path(self, app_dir: Path = APP_DIR) -> Path:
        path = Path(self.output_log_file)
        if path.is_absolute():
            return path
        return app_dir / path

    def resolve_event_log_path(self, app_dir: Path = APP_DIR) -> Path:
        path = Path(self.event_log_file)
        if path.is_absolute():
            return path
        return app_dir / path


def load_settings(config_path: Path = CONFIG_PATH) -> AppSettings:
    if not config_path.exists():
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return AppSettings(**DEFAULT_CONFIG)

    with config_path.open("r", encoding="utf-8") as config_file:
        loaded = json.load(config_file)

    merged = DEFAULT_CONFIG.copy()
    merged.update(loaded)
    merged["region"] = DEFAULT_CONFIG["region"].copy() | loaded.get("region", {})
    return AppSettings(**merged)


def save_language(language: str, config_path: Path = CONFIG_PATH) -> None:
    language = language if language in {"en", "pt", "de"} else "en"
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as config_file:
            loaded = json.load(config_file)
    else:
        loaded = DEFAULT_CONFIG.copy()

    loaded["language"] = language
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(loaded, indent=2), encoding="utf-8")
