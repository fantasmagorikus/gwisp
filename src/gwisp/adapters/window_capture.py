import ctypes
from dataclasses import dataclass

from PIL import Image

try:
    import win32gui
    import win32process
    import win32ui
except ImportError as exc:
    PYWIN32_IMPORT_ERROR: ImportError | None = exc
else:
    PYWIN32_IMPORT_ERROR = None


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    class_name: str
    process_id: int
    width: int
    height: int

    @property
    def display_name(self) -> str:
        return f"{self.title} [{self.width}x{self.height}]"


class WindowCapture:
    def ensure_available(self) -> None:
        if PYWIN32_IMPORT_ERROR is not None:
            raise RuntimeError(
                "Window capture requires pywin32. Run: python -m pip install pywin32"
            ) from PYWIN32_IMPORT_ERROR

    def list_windows(self) -> list[WindowInfo]:
        self.ensure_available()
        windows: list[WindowInfo] = []

        def visit(hwnd: int, _extra: object) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return True

            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = max(0, right - left)
            height = max(0, bottom - top)
            if width < 80 or height < 60:
                return True

            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            windows.append(
                WindowInfo(
                    hwnd=hwnd,
                    title=title,
                    class_name=win32gui.GetClassName(hwnd),
                    process_id=process_id,
                    width=width,
                    height=height,
                )
            )
            return True

        win32gui.EnumWindows(visit, None)
        return sorted(windows, key=lambda window: window.title.lower())

    def capture_window_image(self, hwnd: int) -> Image.Image:
        self.ensure_available()
        if not win32gui.IsWindow(hwnd):
            raise RuntimeError("selected capture window no longer exists")
        if win32gui.IsIconic(hwnd):
            raise RuntimeError(
                "selected capture window is minimized; restore it before OCR capture"
            )

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            raise RuntimeError("selected capture window has invalid dimensions")

        window_dc = win32gui.GetWindowDC(hwnd)
        source_dc = win32ui.CreateDCFromHandle(window_dc)
        memory_dc = source_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(source_dc, width, height)
        memory_dc.SelectObject(bitmap)

        try:
            result = ctypes.windll.user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), 2)
            if result != 1:
                raise RuntimeError("Windows PrintWindow could not capture the selected window")

            bitmap_info = bitmap.GetInfo()
            bitmap_bits = bitmap.GetBitmapBits(True)
            return Image.frombuffer(
                "RGB",
                (bitmap_info["bmWidth"], bitmap_info["bmHeight"]),
                bitmap_bits,
                "raw",
                "BGRX",
                0,
                1,
            ).copy()
        finally:
            win32gui.DeleteObject(bitmap.GetHandle())
            memory_dc.DeleteDC()
            source_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, window_dc)
