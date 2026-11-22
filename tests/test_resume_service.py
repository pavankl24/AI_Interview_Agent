import sys
import types

import pytest

from backend.services.resume_service import _next_question, extract_document, match_job


def test_rejects_invalid_resume_type():
    with pytest.raises(ValueError, match="valid PDF or DOCX"):
        extract_document("resume.txt", "text/plain", b"a sufficiently long body of plain text that cannot be accepted")


def test_rejects_oversized_resume():
    with pytest.raises(ValueError, match="5 MB"):
        extract_document("resume.pdf", "application/pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024))


def test_rejects_scanned_or_empty_pdf(monkeypatch):
    class Page:
        @staticmethod
        def extract_text():
            return ""

    class Reader:
        pages = [Page()]

        def __init__(self, _stream):
            pass

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=Reader))
    with pytest.raises(ValueError, match="No readable resume text"):
        extract_document("resume.pdf", "application/pdf", b"%PDF-1.4\n%%EOF")


def test_extracts_text_from_pdf(monkeypatch):
    class Page:
        @staticmethod
        def extract_text():
            return "Candidate Name\nPython developer with production API experience and database design skills."

    class Reader:
        pages = [Page()]

        def __init__(self, _stream):
            pass

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=Reader))
    text = extract_document("resume.pdf", "application/pdf", b"%PDF-1.4\nvalid")
    assert "Python developer" in text


def test_extracts_text_from_docx(monkeypatch):
    class Paragraph:
        text = "Candidate Name: Python engineer with APIs, systems and database experience."

    class Document:
        paragraphs = [Paragraph()]
        tables = []

        def __init__(self, _stream):
            pass

    monkeypatch.setitem(sys.modules, "docx", types.SimpleNamespace(Document=Document))
    text = extract_document("resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04valid")
    assert "Python engineer" in text


def test_job_match_score_has_defined_denominator(monkeypatch):
    class Message:
        content = '{"required_skills":["Python","SQL","Kubernetes"],"preferred_skills":["AWS"],"required_experience":"2 years","responsibilities":[],"technologies":[],"expectations":[]}'

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    class Completions:
        @staticmethod
        def create(**_kwargs):
            return Response()

    class Chat:
        completions = Completions()

    class FakeGroq:
        chat = Chat()

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr("backend.services.resume_service.Groq", FakeGroq)
    result = match_job({"technical_skills": ["Python", "SQL"], "programming_languages": [], "frameworks_tools": [], "projects": []}, "A sufficiently long job description mentioning Python, SQL and Kubernetes requirements.")
    assert result["matching_skills"] == ["Python", "SQL"]
    assert result["missing_skills"] == ["Kubernetes"]
    assert result["score"] == 67
    assert result["score_explanation"] == "2 of 3 explicitly identified required skills match the resume"


def test_job_match_score_is_unavailable_without_required_skills(monkeypatch):
    class Message:
        content = '{"required_skills":[],"preferred_skills":[],"required_experience":"","responsibilities":[],"technologies":[],"expectations":[]}'

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    class Completions:
        @staticmethod
        def create(**_kwargs):
            return Response()

    class Chat:
        completions = Completions()

    class FakeGroq:
        chat = Chat()

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr("backend.services.resume_service.Groq", FakeGroq)
    result = match_job({"technical_skills": [], "programming_languages": [], "frameworks_tools": [], "projects": []}, "A sufficiently long job description with no machine identified requirements.")
    assert result["score"] is None


def test_generated_question_is_constrained_to_resume_context(monkeypatch):
    captured = {}

    class Message:
        content = "How did you design the task scheduling API in your Campus Planner project?"

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    class Completions:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return Response()

    class Chat:
        completions = Completions()

    class FakeGroq:
        chat = Chat()

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr("backend.services.resume_service.Groq", FakeGroq)
    question = _next_question({"mode":"Project Deep-Dive Interview", "role":"Backend Engineer", "profile":{"projects":[{"name":"Campus Planner","description":"Built a task scheduling API"}]}, "job_description":"", "difficulty":"Medium", "asked":[], "turns":[]}, first=True)
    assert "Campus Planner" in question
    assert "Never invent" in captured["messages"][0]["content"]
    assert "Campus Planner" in captured["messages"][1]["content"]
