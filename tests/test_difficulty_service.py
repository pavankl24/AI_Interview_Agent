from backend.services.difficulty_service import record_score


def test_three_strong_scores_promote_one_level_and_reset_streak():
    difficulty, streak, promoted = record_score("Beginner", 0, 8)
    assert (difficulty, streak, promoted) == ("Beginner", 1, False)

    difficulty, streak, promoted = record_score(difficulty, streak, 7.5)
    assert (difficulty, streak, promoted) == ("Beginner", 2, False)

    assert record_score(difficulty, streak, 7.5) == ("Intermediate", 0, True)


def test_low_score_resets_streak():
    assert record_score("Intermediate", 2, 7.4) == ("Intermediate", 0, False)


def test_advanced_is_a_promotion_cap():
    assert record_score("Advanced", 2, 10) == ("Advanced", 0, False)
