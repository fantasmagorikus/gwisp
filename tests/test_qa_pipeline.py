import datetime as dt

from PIL import Image

from gwisp.config import AppSettings, RegionSettings
from gwisp.services.qa_pipeline import QAPipeline


class FakeScreenCapture:
    def __init__(self) -> None:
        self.last_region = None

    def capture_region_image(self, region):
        self.last_region = region
        return Image.new("RGB", (1, 1))


class FakeOcrEngine:
    def __init__(self, text: str) -> None:
        self.text = text

    def image_to_text(self, image, lang: str) -> str:
        return self.text


class FakeLlmClient:
    def warm_up(self) -> str:
        return "ready"

    def ask(self, question: str) -> str:
        return f"Answer: {question}"


def make_pipeline(text: str) -> QAPipeline:
    return QAPipeline(
        settings=AppSettings(min_chars=3),
        screen_capture=FakeScreenCapture(),
        ocr_engine=FakeOcrEngine(text),
        llm_client=FakeLlmClient(),
    )


def test_pipeline_captures_and_prepares_question() -> None:
    pipeline = make_pipeline("What is 2+2?\nA) 3\nB) 4")

    raw_text = pipeline.capture_region_text()
    decision = pipeline.prepare_question(raw_text)

    assert decision.accepted
    assert "What is 2+2?" in decision.question


def test_pipeline_accepts_override_capture_region() -> None:
    screen_capture = FakeScreenCapture()
    pipeline = QAPipeline(
        settings=AppSettings(min_chars=3),
        screen_capture=screen_capture,
        ocr_engine=FakeOcrEngine("What is DNS?"),
        llm_client=FakeLlmClient(),
    )
    override = RegionSettings(left=10, top=20, width=300, height=140)

    pipeline.capture_region_text(override)

    assert screen_capture.last_region == override


def test_pipeline_ignores_short_text() -> None:
    pipeline = make_pipeline("x")

    decision = pipeline.prepare_question(pipeline.capture_region_text())

    assert not decision.accepted
    assert decision.status == "ignored"


def test_pipeline_tracks_duplicates_after_remembering() -> None:
    pipeline = make_pipeline("What is DNS?")
    decision = pipeline.prepare_question("What is DNS?")
    pipeline.remember_question(decision.question)

    duplicate = pipeline.prepare_question("What is DNS?")

    assert duplicate.status == "duplicate"


def test_pipeline_can_reset_duplicate_history() -> None:
    pipeline = make_pipeline("What is DNS?")
    decision = pipeline.prepare_question("What is DNS?")
    pipeline.remember_question(decision.question)

    pipeline.reset_history()
    repeated = pipeline.prepare_question("What is DNS?")

    assert repeated.accepted


def test_pipeline_delegates_answering() -> None:
    pipeline = make_pipeline("What is DNS?")
    captured_at = dt.datetime(2026, 4, 25, 12, 0, 0)

    answer, returned_at = pipeline.answer_question("What is DNS?", captured_at)

    assert answer == "Answer: What is DNS?"
    assert returned_at == captured_at
