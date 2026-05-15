import difflib

from gwisp.services.text_cleaner import comparable_text


class DuplicateDetector:
    def __init__(self, threshold: float, history_limit: int = 20) -> None:
        self.threshold = threshold
        self.history_limit = history_limit
        self.recent_questions: list[str] = []

    def is_duplicate(self, question: str) -> bool:
        candidate = comparable_text(question)

        for previous in self.recent_questions[-self.history_limit :]:
            ratio = difflib.SequenceMatcher(None, candidate, previous).ratio()
            if ratio >= self.threshold:
                return True

        return False

    def remember(self, question: str) -> None:
        self.recent_questions.append(comparable_text(question))
        self.recent_questions = self.recent_questions[-self.history_limit :]

    def reset(self) -> None:
        self.recent_questions.clear()
