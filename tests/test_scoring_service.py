from backend.services.scoring_service import normalize_score


def test_score_is_clamped_to_the_existing_ten_point_scale():
    assert normalize_score(-2) == 0
    assert normalize_score(12) == 10
    assert normalize_score(7.46) == 7.5


def test_invalid_score_defaults_to_zero():
    assert normalize_score("not a score") == 0
    assert normalize_score(float("nan")) == 0
