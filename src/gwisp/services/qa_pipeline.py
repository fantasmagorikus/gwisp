import datetime as dt

from gwisp.config import AppSettings, RegionSettings
from gwisp.domain.models import QuestionDecision
from gwisp.domain.ports import LlmClient, OcrEngine, ScreenCapture
from gwisp.services.duplicate_detector import DuplicateDetector
from gwisp.services.text_cleaner import (
    APP_WINDOW_STATUS,
    clean_ocr_text,
    compact_length,
    looks_like_app_window,
)


class QAPipeline:
    def __init__(
        self,
        settings: AppSettings,
        screen_capture: ScreenCapture,
        ocr_engine: OcrEngine,
        llm_client: LlmClient,
        duplicate_detector: DuplicateDetector | None = None,
    ) -> None:
        self.settings = settings
        self.screen_capture = screen_capture
        self.ocr_engine = ocr_engine
        self.llm_client = llm_client
        self.duplicate_detector = duplicate_detector or DuplicateDetector(
            threshold=settings.duplicate_threshold
        )

    def capture_region_text(self, region: RegionSettings | None = None) -> str:
        capture_region = region or self.settings.region
        image = self.screen_capture.capture_region_image(capture_region)
        return self.ocr_engine.image_to_text(image, lang=self.settings.ocr_lang)

    def prepare_question(self, raw_text: str) -> QuestionDecision:
        question = clean_ocr_text(raw_text)
        if compact_length(question) < self.settings.min_chars:
            return QuestionDecision(
                status="ignored",
                message="OCR text ignored; shorter than min_chars",
                question=question,
            )

        if looks_like_app_window(question):
            return QuestionDecision(status="ignored", message=APP_WINDOW_STATUS, question=question)

        if self.duplicate_detector.is_duplicate(question):
            return QuestionDecision(
                status="duplicate",
                message="duplicate OCR question ignored",
                question=question,
            )

        return QuestionDecision(
            status="accepted",
            message="new OCR question sent to Ollama",
            question=question,
        )

    def remember_question(self, question: str) -> None:
        self.duplicate_detector.remember(question)

    def reset_history(self) -> None:
        self.duplicate_detector.reset()

    def answer_question(self, question: str, captured_at: dt.datetime) -> tuple[str, dt.datetime]:
        return self.llm_client.ask(question), captured_at
