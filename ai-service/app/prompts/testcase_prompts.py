from typing import List

from .guardrails import GUARDRAILS

TESTCASE_PROMPT_VERSION = "testcase-v3"

TESTCASE_PROMPT_TEMPLATE = """You are a Principal QA Automation Architect and Lead Quality Engineer.
Your task is to analyze the provided requirement, acceptance criteria, and retrieved knowledge context to generate rigorous, production-grade test cases.

{guardrails}

CRITICAL GROUNDING AND QUALITY RULES:
1. Ground every test case strictly in the provided requirement and retrieved context.
2. Do not hallucinate nonexistent features, database columns, or fictional UI controls.
3. If specific requirement identifiers exist in context (for example AC-001, FR-002, BR-003), reference them in the scenario title or description.
4. Internally classify each scenario using the following test type guidance:
   - POSITIVE: Happy paths verifying core functionality and business rules.
   - NEGATIVE: Invalid inputs, invalid states, validation failures, and error handling.
   - EDGE: Boundary conditions, null/empty values, unusual inputs, concurrency,
     large payloads, or timeout scenarios ONLY when relevant to the supplied
     requirement, acceptance criteria, or context.
   - SECURITY: Authentication, authorization, injection, access control, or
     sensitive-data scenarios ONLY when relevant to the supplied system behavior.
   - PERFORMANCE: Throughput, latency, load, concurrency, or large-volume
     scenarios ONLY when supported or reasonably implied by the supplied material.
5. Internally assess the relative execution priority of each scenario as HIGH, MEDIUM, or LOW so the most important coverage is represented first.
6. Provide actionable, step-by-step reproduction instructions and precise expected results.
7. Provide concrete preconditions such as test data state, user permissions, and system configuration.
8. Do not invent security requirements, performance thresholds, API behavior,
database states, HTTP status codes, error messages, or system configurations
that are not supported by the supplied sources.

REQUIREMENT:
{requirement}

ACCEPTANCE CRITERIA:
{acceptanceCriteria}

REQUESTED TEST COVERAGE TYPES:
{testTypes}

RETRIEVED CONTEXT (AUTHORITATIVE KNOWLEDGE BASE):
{context}

Output strictly as a valid JSON array matching this response schema for each object.
The internal test type and priority assessment is for reasoning only. Do not include `type` or `priority` keys in the JSON response, do not mention them in any response field, and do not replace them with another field.
[
  {{
    "scenario": "Descriptive, unique test scenario name",
    "preconditions": ["Exact precondition 1"],
    "steps": ["Step 1 description", "Step 2 description"],
    "expectedResult": "Detailed assertion describing the observable outcome"
  }}
]
"""


def build_testcase_prompt(requirement: str, acceptance_criteria: str, test_types: List[str], context: str) -> str:
    ctx = context.strip() if context and context.strip() else (
        "No document context available. Ground solely on the provided requirement "
        "without inventing external details."
    )
    resolved_types = test_types or [
        "Functional Tests",
        "Edge & Boundary Cases",
        "Security & Validation",
        "Performance & Load"
    ]
    return TESTCASE_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        requirement=requirement,
        acceptanceCriteria=acceptance_criteria or "",
        testTypes=", ".join(resolved_types),
        context=ctx
    )


FILE_TESTCASE_PROMPT_TEMPLATE = """You are a Principal QA Architect and Automation Engineer.
Your task is to generate rigorous, production-grade test cases based on the provided input materials.

{guardrails}

CRITICAL FIDELITY RULES:
1. The supplied documents and code are the sole authoritative source.
2. Formulate comprehensive scenarios aligned directly with the requested coverage types:
   - Functional Tests: Core user journeys, business flows, valid inputs, and expected outcomes.
   - Edge and Boundary Cases: Min/max bounds, null/empty states, unusual inputs,
     concurrency, large payloads, or timeout scenarios ONLY when relevant to the
     supplied requirements, acceptance criteria, or source code.
   - Security and Validation: Authentication, authorization, injection protection,
     access control, sensitive-data handling, or input validation ONLY when relevant
     to the supplied requirements or implementation.
   - Performance and Load: High volume, large payload, latency, throughput,
     concurrency, or resource-stress scenarios ONLY when supported or reasonably
     implied by the supplied requirements or implementation.
2a. Do not invent security requirements, performance thresholds, API behavior,
database states, HTTP status codes, error messages, or system configurations
that are not supported by the supplied sources.
3. Internally classify each scenario as POSITIVE, NEGATIVE, EDGE, SECURITY, or PERFORMANCE.
4. Internally assess each scenario priority as HIGH, MEDIUM, or LOW and order the most important coverage first.
5. If both BRD and project source code are provided, cross-reference business specifications against the implementation.
6. If only project code is provided, inspect endpoints, services, error handlers, and business logic.
7. If only a BRD is provided, extract business rules, workflows, validations, and edge cases.
8. Provide specific preconditions and step-by-step execution instructions.

INPUT MODE: {mode}
REQUESTED TEST COVERAGE TYPES: {test_types}

{content_section}

Output strictly as a valid JSON array matching this schema for each object.
Use type and priority only for internal reasoning. Do not include `type` or `priority` keys anywhere in the JSON response, and do not replace them with another field.
[
  {{
    "tcId": "TC-001",
    "requirementId": "BRD §4.3.1.1 / AC-001",
    "scenario": "Descriptive test scenario title",
    "preconditions": ["condition 1", "condition 2"],
    "steps": ["Step 1 description", "Step 2 description"],
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
    resolved_types = test_types or [
        "Functional Tests",
        "Edge & Boundary Cases",
        "Security & Validation",
        "Performance & Load"
    ]

    content_parts = []
    if brd_text and brd_text.strip():
        content_parts.append(f"### BUSINESS REQUIREMENTS DOCUMENT (BRD):\n{brd_text.strip()}")
    if zip_summary and zip_summary.strip():
        content_parts.append(f"### PROJECT SOURCE CODE AND STRUCTURE (FROM ZIP):\n{zip_summary.strip()}")
    if not content_parts:
        content_parts.append("No document or code content provided.")

    mode_label = {
        "brd": "BRD Document Analysis",
        "zip": "Project Source Code ZIP Analysis",
        "both": "BRD Requirements and Project Source Code Cross-Verification"
    }.get(mode.lower(), mode.upper())

    return FILE_TESTCASE_PROMPT_TEMPLATE.format(
        guardrails=GUARDRAILS,
        mode=mode_label,
        test_types=", ".join(resolved_types),
        content_section="\n\n".join(content_parts)
    )