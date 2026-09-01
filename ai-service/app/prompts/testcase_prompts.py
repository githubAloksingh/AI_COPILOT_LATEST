from typing import List
from .guardrails import GUARDRAILS

TESTCASE_PROMPT_VERSION = "testcase-v1"

TESTCASE_PROMPT_TEMPLATE = """You are an expert QA automation engineer. Your task is to generate positive, negative, and edge test cases based on the provided requirement and acceptance criteria.

{guardrails}

REQUIREMENT: {requirement}
ACCEPTANCE CRITERIA: {acceptanceCriteria}
TEST TYPES: {testTypes}

RETRIEVED CONTEXT: {context}

Output strictly as a valid JSON array matching this schema for each object:
[
  {{
    "scenario": "The test scenario",
    "type": "POSITIVE or NEGATIVE or EDGE",
    "priority": "HIGH or MEDIUM or LOW",
    "preconditions": ["condition 1"],
    "steps": ["step 1", "step 2"],
    "expectedResult": "expected outcome"
  }}
]
"""


def build_testcase_prompt(requirement: str, acceptance_criteria: str, test_types: List[str], context: str) -> str:
    ctx = context.strip() if context and context.strip() else "No context available."
    test_types_str = ", ".join(test_types) if test_types else "POSITIVE, NEGATIVE, EDGE"
    return TESTCASE_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        requirement=requirement,
        acceptanceCriteria=acceptance_criteria or "",
        testTypes=test_types_str,
        context=ctx
    )
