from typing import Literal

from .scoring_service import PROMOTION_THRESHOLD, normalize_score

Difficulty = Literal["Beginner", "Intermediate", "Advanced"]
_LEVELS: tuple[Difficulty, ...] = ("Beginner", "Intermediate", "Advanced")
PROMOTION_STREAK = 3


def record_score(difficulty: Difficulty, streak: int, score: object) -> tuple[Difficulty, int, bool]:
    normalized_score = normalize_score(score)
    if normalized_score < PROMOTION_THRESHOLD:
        return difficulty, 0, False
    next_streak = streak + 1
    if next_streak < PROMOTION_STREAK:
        return difficulty, next_streak, False
    level_index = _LEVELS.index(difficulty)
    if level_index >= len(_LEVELS) - 1:
        return difficulty, 0, False
    return _LEVELS[level_index + 1], 0, True
