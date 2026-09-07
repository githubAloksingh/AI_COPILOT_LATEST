from typing import List
from .guardrails import GUARDRAILS

TESTCASE_PROMPT_VERSION = "testcase-v2"

TESTCASE_PROMPT_TEMPLATE = """You are a Principal QA Automation Architect and Lead Quality Engineer.
Your task is to analyze the provided requirement, acceptance criteria, and retrieved knowledge context to generate rigorous, production-grade test cases.

{guardrails}

CRITICAL GROUNDING & QUALITY RULES:
1. Ground every test case strictly in the provided requirement and retrieved context.
2. DO NOT hallucinate nonexistent features, database columns, or fictional UI controls.
3. If specific requirement identifiers exist in context (e.g. AC-001, FR-002, BR-003), explicitly reference them in the scenario title or description.
4. Categorize test cases into appropriate types:
   - "POSITIVE": Happy path verifying core functionality and business rules.
   - "NEGATIVE": Invalid inputs, unexpected states, boundary violations, and error handling.
   - "EDGE": Concurrency, race conditions, empty/null values, extremely large payloads, and timeout scenarios.
   - "SECURITY": Input validation, SQL injection/XSS attempts, unauthorized access, and sensitive data handling.
   - "PERFORMANCE": High throughput, latency limits, large volume data queries.
5. Provide actionable, step-by-step reproduction instructions and precise expected results.
6. Provide concrete preconditions (e.g., test data state, user permissions, system configuration).

REQUIREMENT:
{requirement}

ACCEPTANCE CRITERIA:
{acceptanceCriteria}

REQUESTED TEST COVERAGE TYPES:
{testTypes}

RETRIEVED CONTEXT (AUTHORITATIVE KNOWLEDGE BASE):
{context}

Output strictly as a valid JSON array matching this schema for each object:
[
  {{
    "scenario": "Descriptive, unique test scenario name (e.g. [AC-001] Verify successful order placement with valid card)",
    "type": "POSITIVE or NEGATIVE or EDGE or SECURITY or PERFORMANCE",
    "priority": "HIGH or MEDIUM or LOW",
    "preconditions": [
      "Exact precondition 1 (e.g. User account exists with verified email)"
    ],
    "steps": [
      "Step 1: Navigate to checkout page",
      "Step 2: Enter valid 16-digit card number and future expiry",
      "Step 3: Click 'Pay Now'"
    ],
    "expectedResult": "Detailed assertion (e.g. HTTP 200 returned, order status updated to CONFIRMED, email notification triggered)"
  }}
]
"""


def build_testcase_prompt(requirement: str, acceptance_criteria: str, test_types: List[str], context: str) -> str:
    ctx = context.strip() if context and context.strip() else "No document context available. Ground solely on provided requirement without inventing external details."
    test_types_str = ", ".join(test_types) if test_types else "POSITIVE, NEGATIVE, EDGE, SECURITY, PERFORMANCE"
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

CRITICAL FIDELITY RULES:
1. The supplied documents/code are the SOLE AUTHORITATIVE SOURCE.
2. Formulate comprehensive test scenarios aligned directly with the requested TEST COVERAGE TYPES:
   - Functional Tests: Core user journeys, business flows, valid inputs, and expected outcomes.
   - Edge & Boundary Cases: Min/max bounds, null/empty states, unexpected data formats, concurrency, and race conditions.
   - Security & Validation: Authentication, authorization, SQL injection/XSS sanitization, rate limiting, and input validation.
   - Performance & Load: High volume, large payload, latency thresholds, and resource stress behaviors.
3. If both BRD and Project Source Code are provided, cross-reference the business specifications against the actual code implementation. Identify test cases that confirm adherence or uncover discrepancies/gaps.
4. If only Project ZIP code is provided, inspect controller endpoints, service methods, error handlers, and business logic to derive realistic test scenarios.
5. If only BRD is provided, extract all business rules, workflows, validations, and edge cases.
6. Provide specific, clear preconditions and step-by-step instructions for execution.

INPUT MODE: {mode}
REQUESTED TEST COVERAGE TYPES: {test_types}

{content_section}

Output strictly as a valid JSON array matching this schema for each object:
[
  {{
    "scenario": "Descriptive test scenario title",
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
    types_list = test_types or ["Functional Tests", "Edge & Boundary Cases", "Security & Validation"]
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
