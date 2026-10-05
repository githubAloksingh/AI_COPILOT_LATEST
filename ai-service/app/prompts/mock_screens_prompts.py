from app.prompts.guardrails import GUARDRAILS

MOCK_SCREENS_PROMPT_VERSION = "mock-screens-plan-v2"
MOCK_SCREENS_SUMMARY_PROMPT_VERSION = "mock-screens-context-v2"
MOCK_SCREEN_GENERATION_PROMPT_VERSION = "mock-screen-spec-v2"


def build_mock_screens_context_prompt(chunk_group: str, chunk_range: str) -> str:
    return f"""{GUARDRAILS}

Analyze this portion of the selected Business Requirements Document (BRD).
Source chunk range: {chunk_range}

Extract requirements, workflows, and constraints explicitly supported by this BRD portion. Preserve concrete names, rules, and conditions. Do not infer missing requirements. Return JSON with exactly these list fields: requirements, workflows, constraints.

BRD CONTENT:
{chunk_group}
"""


def build_mock_screens_plan_prompt(summarized_context: str) -> str:
    return f"""{GUARDRAILS}

Create an ordered screen plan covering the user workflows and requirements documented in the selected BRD. The following evidence was extracted from every chunk of that BRD and is the sole source of product facts. Include the screens needed to support its documented workflows; do not invent requirements.

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
    sequence: int,
    screen_name: str,
    purpose: str,
    relevant_requirements: list[str],
    brd_context: str,
    previous_screens: str
) -> str:
    return f"""{GUARDRAILS}

Generate exactly one structured screen specification for screen {sequence}: {screen_name}.

PLANNED SCREEN PURPOSE:
{purpose}

BRD REQUIREMENTS ASSIGNED TO THIS SCREEN:
{relevant_requirements}

ADDITIONAL RETRIEVED BRD CONTEXT:
{brd_context}

PREVIOUSLY COMPLETED SCREENS (for navigation and terminology consistency only):
{previous_screens}

Return exactly one JSON object using these exact keys and types: "sequence" (integer, exactly {sequence}), "screenName" (string, exactly "{screen_name}"), "purpose" (string), "layoutDescription" (string), "components" (non-empty array of objects with "componentType", "label", "description", "required", and "options"), and "interactionNotes" (array of strings). Do not rename keys to alternatives such as screenNumber, screenSequence, screenPurpose, or layout. Use only these componentType values: header, navigation, text, button, input, select, checkbox, radio, table, card, modal, alert, imagePlaceholder.

VISUAL DIRECTION:
- Derive screen content, fields, and actions from the BRD requirements assigned to this screen and its retrieved BRD context.
- The renderer supplies PCP branding and persistent navigation. Use components for screen-specific content rather than repeating the full navigation.
- Build a compact enterprise screen with a header, clearly named sections/cards, relevant filters/context where applicable, concise fields, a table for record lists, visible status/alerts, and screen-appropriate actions. Keep component order in a natural reading order and avoid redundant content.
- For tables, put concise column headings and, where useful, one illustrative fictional sample row in "options" as strings separated by " | ". Identify sample data as illustrative in the description; do not invent business rules or imply sample values came from the BRD.
- Use labels such as "FILTERS / CONTEXT" for applicable tracker/report filters and actionable buttons supported by the screen purpose, such as Search, Reset, View Details, Update, Approve, Reject, Save, Export PDF, or Export Excel.

Do not return HTML, CSS, JavaScript, SVG, code, URLs, or images. The output is an abstract specification for later backend rendering, not a rendered screen. Use BRD evidence as the source of truth and do not invent product requirements.
"""