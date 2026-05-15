from typing import Protocol

from PIL import Image

from gwisp.config import RegionSettings


class ScreenCapture(Protocol):
    def capture_region_image(self, region: RegionSettings) -> Image.Image:
        raise NotImplementedError


class OcrEngine(Protocol):
    def image_to_text(self, image: Image.Image, lang: str) -> str:
        raise NotImplementedError


class LlmClient(Protocol):
    def warm_up(self) -> str:
        raise NotImplementedError

    def ask(self, question: str) -> str:
        raise NotImplementedError
