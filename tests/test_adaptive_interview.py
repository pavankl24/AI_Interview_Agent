import json
from types import SimpleNamespace

import pytest

from backend.services.ai_service import InterviewAgent


def agent_with_response(monkeypatch, classification, score, action="NEXT_QUESTION", followup_count=0):
    agent = InterviewAgent.__new__(InterviewAgent)
    agent.interview_type = "Python"
    agent.difficulty = "Intermediate"
    agent.interview_mode = "Technical conversation"
    agent.messages = []
    agent.asked_questions = ["What is a list?"]
    agent.evaluation_history = []
    agent.client = None
    payload = {
        "evaluation": {"classification": classification, "correctness_score": score,
                       "understanding_level": "Intermediate", "strengths": ["Clear definition"],
                       "missing_concepts": ["mutability"], "feedback": "Explain the tradeoff briefly."},
        "interview_decision": {"action": action, "reason": "Assess the concept.",
                               "next_difficulty": "Medium", "next_question": "How does tuple immutability help?",
                               "topic": "Python"},
    }

    class Completion:
        choices = [SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]

    monkeypatch.setattr(agent, "_completion", lambda _messages: Completion())
    return agent, followup_count


@pytest.mark.parametrize("classification,score,expected_action", [
    ("Partially Correct", 5, "FOLLOW_UP"),
    ("Incorrect", 2, "FOLLOW_UP"),
    ("Incomplete", 3, "FOLLOW_UP"),
    ("Excellent", 9, "NEXT_QUESTION"),
])
def test_answer_classification_drives_followup_and_difficulty(monkeypatch, classification, score, expected_action):
    agent, count = agent_with_response(monkeypatch, classification, score)
    result, _ = agent.assess_answer("What is a list?", "A sequence of values.", followup_count=count)
    assert result["action"] == expected_action
    assert result["score"] == score
    if expected_action == "FOLLOW_UP":
        expected_difficulty = "Easy" if classification == "Incorrect" else "Medium"
        assert result["next_difficulty"] == expected_difficulty
    else:
        assert result["next_difficulty"] in {"Medium", "Hard"}


def test_followup_limit_forces_next_question(monkeypatch):
    agent, _ = agent_with_response(monkeypatch, "Incomplete", 2)
    result, _ = agent.assess_answer("What is a list?", "", followup_count=2)
    assert result["action"] == "NEXT_QUESTION"


def test_malformed_model_output_is_rejected(monkeypatch):
    agent, _ = agent_with_response(monkeypatch, "Good", 8)

    class Completion:
        choices = [SimpleNamespace(message=SimpleNamespace(content='{"evaluation":{}}'))]

    monkeypatch.setattr(agent, "_completion", lambda _messages: Completion())
    with pytest.raises(ValueError, match="invalid response"):
        agent.assess_answer("What is a list?", "A sequence.")


def test_adaptive_history_and_difficulty_survive_agent_state_reload(monkeypatch):
    agent, _ = agent_with_response(monkeypatch, "Excellent", 9)
    result, _ = agent.assess_answer("What is a list?", "A sequence of values.")
    state = agent.export_state()
    monkeypatch.setattr("backend.services.ai_service.Groq", lambda **_kwargs: None)
    restored = InterviewAgent.from_state(state)
    assert restored.difficulty == agent.difficulty
    assert restored.asked_questions == agent.asked_questions
    assert restored.evaluation_history[0]["classification"] == result["classification"]
