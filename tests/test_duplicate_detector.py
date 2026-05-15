from gwisp.services.duplicate_detector import DuplicateDetector


def test_duplicate_detector_matches_similar_questions() -> None:
    detector = DuplicateDetector(threshold=0.9)
    detector.remember("Which port does HTTP use? A) 22 B) 80")

    assert detector.is_duplicate("Which port does HTTP use? A) 22 B) 80")


def test_duplicate_detector_rejects_different_questions() -> None:
    detector = DuplicateDetector(threshold=0.9)
    detector.remember("Which port does HTTP use? A) 22 B) 80")

    assert not detector.is_duplicate("What does DNS resolve?")
