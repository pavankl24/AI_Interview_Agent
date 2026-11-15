from math import isfinite

MAX_SCORE = 10.0
PROMOTION_THRESHOLD = 7.5


def normalize_score(value: object) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not isfinite(score):
        return 0.0
    return round(min(MAX_SCORE, max(0.0, score)), 1)
