from app.prompts.guardrails import GUARDRAILS

MOCK_SCREENS_PROMPT_VERSION = "mock-screens-plan-v1"
MOCK_SCREENS_SUMMARY_PROMPT_VERSION = "mock-screens-context-v1"
MOCK_SCREEN_GENERATION_PROMPT_VERSION = "mock-screen-spec-v1"


def build_mock_screens_context_prompt(chunk_group: str, chunk_range: str, user_prompt: str) -> str:
    return f"""{GUARDRAILS}

Analyze this portion of the selected Business Requirements Document (BRD).
The user's requested mock-screen scope is: {user_prompt}
Source chunk range: {chunk_range}

Extract only requirements, workflows, and constraints that are explicitly supported by this BRD portion and relevant to the requested scope. Keep concrete names, rules, and conditions. Do not infer missing requirements. Return JSON with exactly these list fields: requirements, workflows, constraints.

BRD CONTENT:
{chunk_group}
"""


def build_mock_screens_plan_prompt(user_prompt: str, summarized_context: str) -> str:
    return f"""{GUARDRAILS}

Create an ordered screen plan for the requested mock-screen scope.
USER REQUESTED SCOPE:
{user_prompt}

The following evidence was extracted from every chunk of the selected BRD. Treat this BRD-derived evidence as the source of truth. The user prompt defines scope, not new product facts. Include only screens needed for that scope and do not invent requirements.

BRD-DERIVED EVIDENCE:
{summarized_context}

Return one JSON object with a non-empty "screens" array. Each screen must contain:
- "sequence": integer, starting at 1 with no gaps; list order is the canonical order.
- "screenName": concise user-facing name.
- "purpose": the user goal served by this screen.
- "relevantRequirements": one or more concise requirements/workflow/constraint statements copied or faithfully summarized from the BRD-derived evidence.

Order screens deterministically: primary user journey from entry to completion, then supporting/administrative screens, then exception or recovery screens. For screens at the same journey stage, retain the order of first appearance in the BRD evidence. Do not return screen layouts, HTML, CSS, images, or implementation details.
"""


def build_mock_screen_generation_prompt(
    user_prompt: str,
    sequence: int,
    screen_name: str,
    purpose: str,
    relevant_requirements: list[str],
    brd_context: str,
    previous_screens: str
) -> str:
    return f"""{GUARDRAILS}

Generate exactly one structured screen specification for screen {sequence}: {screen_name}.
USER REQUESTED SCOPE:
{user_prompt}

PLANNED SCREEN PURPOSE:
{purpose}

BRD REQUIREMENTS ASSIGNED TO THIS SCREEN:
{relevant_requirements}

ADDITIONAL RETRIEVED BRD CONTEXT:
{brd_context}

PREVIOUSLY COMPLETED SCREENS (for navigation and terminology consistency only):
{previous_screens}

Return exactly one JSON object using these exact keys and types: "sequence" (integer, exactly {sequence}), "screenName" (string, exactly "{screen_name}"), "purpose" (string), "layoutDescription" (string), "components" (non-empty array of objects with "componentType", "label", "description", "required", and "options"), and "interactionNotes" (array of strings). Do not rename keys to alternatives such as screenNumber, screenSequence, screenPurpose, or layout. Use only these componentType values: header, navigation, text, button, input, select, checkbox, radio, table, card, modal, alert, imagePlaceholder. Do not return HTML, CSS, JavaScript, SVG, code, URLs, or images. The output is an abstract specification for later backend rendering, not a rendered screen. Use BRD evidence as the source of truth and do not invent product requirements.
"""