from app.services.gemini_service import GeminiService
from app.prompts import (
    build_requirement_prompt,
    build_testcase_prompt,
    build_defect_prompt,
    build_release_notes_prompt,
    build_daily_status_prompt,
    GUARDRAILS
)
from app.api.schemas import RequirementResult, DefectResult


def test_clean_json_markdown():
    raw = "```json\n{\"summary\": \"Test summary\", \"userStory\": \"Story\"}\n```"
    cleaned = GeminiService.clean_json(raw)
    assert cleaned == "{\"summary\": \"Test summary\", \"userStory\": \"Story\"}"


def test_clean_json_with_prose():
    raw = "Here is the response:\n{\"summary\": \"Test summary\"}\nHope this helps!"
    cleaned = GeminiService.clean_json(raw)
    assert cleaned == "{\"summary\": \"Test summary\"}"


def test_prompt_builders_include_guardrails():
    req_prompt = build_requirement_prompt("User login", "User context")
    assert GUARDRAILS in req_prompt
    assert "User login" in req_prompt
    assert "User context" in req_prompt

    tc_prompt = build_testcase_prompt("User login", "Must enter valid pass", ["POSITIVE"], "Context")
    assert GUARDRAILS in tc_prompt
    assert "POSITIVE" in tc_prompt

    defect_prompt = build_defect_prompt("500 Error", "NullPointer", "stack trace", "step 1", "crash", "success", "Context")
    assert GUARDRAILS in defect_prompt
    assert "500 Error" in defect_prompt
