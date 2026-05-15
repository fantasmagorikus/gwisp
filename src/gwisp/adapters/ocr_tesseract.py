import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

import pytesseract
from PIL import Image

from gwisp.config import APP_DIR, AppSettings


def first_output_line(stdout: str, stderr: str) -> str:
    output = stdout or stderr or ""
    lines = output.splitlines()
    return lines[0] if lines else "(no output)"


class TesseractOcr:
    def __init__(self, settings: AppSettings, app_dir: Path = APP_DIR) -> None:
        self.settings = settings
        self.app_dir = app_dir
        self.tesseract_path = self.configure_runtime()

    def configure_runtime(self) -> Path | None:
        configured_path = Path(str(self.settings.tesseract_cmd))
        selected_path: Path | None = None

        if configured_path.exists():
            selected_path = configured_path
        elif self.settings.tesseract_auto_detect:
            selected_path = self.find_tesseract(self.app_dir)

        if selected_path:
            selected_path = selected_path.resolve()
            pytesseract.pytesseract.tesseract_cmd = str(selected_path)

            bin_dir = str(selected_path.parent)
            current_path = os.environ.get("PATH", "")
            if bin_dir.lower() not in current_path.lower():
                os.environ["PATH"] = bin_dir + os.pathsep + current_path

            tessdata = (
                selected_path.parents[2] / "share" / "tessdata"
                if len(selected_path.parents) > 2
                else None
            )
            if tessdata and tessdata.exists():
                os.environ.setdefault("TESSDATA_PREFIX", str(tessdata))

            return selected_path

        pytesseract.pytesseract.tesseract_cmd = str(configured_path)
        return None

    @staticmethod
    def find_tesseract(app_dir: Path = APP_DIR) -> Path | None:
        candidates = [
            app_dir / ".tools" / "tess-env" / "Library" / "bin" / "tesseract.exe",
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]

        path_candidate = shutil.which("tesseract.exe") or shutil.which("tesseract")
        if path_candidate:
            candidates.append(Path(path_candidate))

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def image_to_text(self, image: Image.Image, lang: str) -> str:
        return pytesseract.image_to_string(image, lang=lang)

    def version_line(self) -> str:
        if not self.tesseract_path:
            raise RuntimeError("Tesseract not found")

        version = subprocess.run(  # nosec B603
            [str(self.tesseract_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return first_output_line(version.stdout, version.stderr)

    def available_languages(self) -> set[str]:
        if not self.tesseract_path:
            raise RuntimeError("Tesseract not found")

        langs = subprocess.run(  # nosec B603
            [str(self.tesseract_path), "--list-langs"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return set((langs.stdout or "").split())
