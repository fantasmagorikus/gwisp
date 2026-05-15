import mss
from PIL import Image

from gwisp.config import RegionSettings


class MssScreenCapture:
    def capture_region_image(self, region: RegionSettings) -> Image.Image:
        with mss.MSS() as screen_capture:
            screenshot = screen_capture.grab(region.as_mss_region())
            return Image.frombytes("RGB", screenshot.size, screenshot.rgb)
