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


FILE_TESTCASE_PROMPT_TEMPLATE = """You are a Principal QA Architect and Automation Engineer.
Your task is to generate rigorous, production-grade test cases based on the provided input materials.

{guardrails}

INPUT MODE: {mode}
REQUESTED TEST COVERAGE TYPES: {test_types}

{content_section}

INSTRUCTIONS:
1. Thoroughly examine the provided materials.
2. Formulate comprehensive test scenarios aligned directly with the requested TEST COVERAGE TYPES:
   - If Functional Tests are requested: Cover core user journeys, business flows, valid inputs, and expected outcomes.
   - If Edge & Boundary Cases are requested: Cover min/max bounds, null/empty states, unexpected data formats, concurrency, and race conditions.
   - If Security & Validation are requested: Cover authentication, authorization, SQL injection/XSS sanitization, rate limiting, and input validation.
   - If Performance & Load are requested: Cover high volume, large payload, latency thresholds, and resource stress behaviors.
3. If both BRD and Project Source Code are provided, cross-reference the business specifications against the actual code implementation. Identify test cases that confirm adherence or uncover discrepancies/gaps.
4. If only Project ZIP code is provided, inspect controller endpoints, service methods, error handlers, and business logic to derive realistic test scenarios.
5. If only BRD is provided, extract all business rules, workflows, validations, and edge cases.
6. Provide specific, clear preconditions and step-by-step instructions for execution.

Output strictly as a valid JSON array matching this schema for each object:
[
  {{
    "scenario": "Clear, descriptive test scenario title",
    "type": "POSITIVE or NEGATIVE or EDGE or SECURITY or PERFORMANCE",
    "priority": "HIGH or MEDIUM or LOW",
    "preconditions": ["condition 1", "condition 2"],
    "steps": ["Step 1 description", "Step 2 description", "Step 3 description"],
    "expectedResult": "Detailed expected outcome"
  }}
]
"""


def build_testcase_from_files_prompt(
    mode: str,
    brd_text: str = "",
    zip_summary: str = "",
    test_types: List[str] = None
) -> str:
    types_list = test_types or ["Functional Tests", "Edge & Boundary Cases"]
    test_types_str = ", ".join(types_list)

    content_parts = []
    if brd_text and brd_text.strip():
        content_parts.append(f"### BUSINESS REQUIREMENTS DOCUMENT (BRD):\n{brd_text.strip()}")
    if zip_summary and zip_summary.strip():
        content_parts.append(f"### PROJECT SOURCE CODE & STRUCTURE (FROM ZIP):\n{zip_summary.strip()}")

    if not content_parts:
        content_parts.append("No document or code content provided.")

    mode_label = {
        "brd": "BRD Document Analysis",
        "zip": "Project Source Code ZIP Analysis",
        "both": "BRD Requirements + Project Source Code Cross-Verification"
    }.get(mode.lower(), mode.upper())

    return FILE_TESTCASE_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        mode=mode_label,
        test_types=test_types_str,
        content_section="\n\n".join(content_parts)
    )

