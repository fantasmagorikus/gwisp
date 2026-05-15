import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class QuestionDecision:
    status: str
    message: str
    question: str = ""

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    captured_at: dt.datetime
