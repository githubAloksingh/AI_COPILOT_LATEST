from typing import Optional

from app.prompts.guardrails import GUARDRAILS

MOCK_SCREENS_PROMPT_VERSION = "mock-screens-plan-v2"
MOCK_SCREENS_SUMMARY_PROMPT_VERSION = "mock-screens-context-v2"
MOCK_SCREEN_GENERATION_PROMPT_VERSION = "mock-screen-spec-v2"

MOCK_SCREEN_PLAN_SYSTEM_PROMPT = """You are a Senior Product Architect, UX Architect, and Principal Business Analyst specializing in enterprise application systems.

Your objective is to analyze the supplied Business Requirements Document (BRD) content and architect a grounded UI screen flow, specifications, and design system. If the supplied content is marked as an excerpt, do not claim coverage of omitted requirements.

CRITICAL RULES:
1. GROUNDED IN SOURCE: Derive all application features, entities, workflows, screens, fields, tables, actions, and validation rules directly from the supplied BRD content.
2. DYNAMIC SCREEN DISCOVERY: DO NOT assume a fixed list of screens or fixed screen count. Different BRDs have completely different screen counts, journeys, and purposes. Derive the count from the supplied source.
3. EXHAUSTIVE COVERAGE: Every distinct feature, workflow, entity lifecycle, approval step, report, and configuration panel mentioned in the BRD must have a corresponding screen. DO NOT skip or merge screens to shorten the output.
4. LOGICAL USER JOURNEY: Determine the natural, logical progression from initial entry/login to main working queues, detail forms, approval checkpoints, settlements, reports, and audit trails as mandated by the BRD.
5. SCREEN TYPES: Choose realistic enterprise screen types appropriate for each requirement (e.g., login, dashboard, work_queue, detail_view, create_form, edit_form, approval_checkpoint, workflow_stepper, adhoc_report, audit_trail, document_viewer, configuration, error_exception).
6. TASK-SPECIFIC CONTENT: Include only fields, tables, metrics, actions, statuses, and rules that serve the screen's BRD-defined task. Do not force KPI tiles, tables, or forms onto every screen and do not invent sample business facts.
7. DESIGN SYSTEM: Formulate a cohesive enterprise color palette and visual design context that reflects the business domain (e.g. Banking, Healthcare, Supply Chain, Insurance).
8. DISTINCT COMPOSITION: Assign each screen a screen_type that accurately expresses its user task. Use overview layouts for monitoring, work queues for triage, focused forms for data entry, split case workspaces for record review, document-review layouts for document inspection, report layouts for analysis, and decision panels for approvals. Screens in one application share their visual identity, not an identical content structure.
9. COMPLETE JSON OUTPUT: You MUST output the complete JSON. Do NOT truncate, do NOT stop mid-array, do NOT summarize remaining screens. The JSON must contain all screens from screen 1 to the last screen. If you are about to run out of space, write shorter but still include EVERY screen.
10. RETURN VALID JSON ONLY: Return a single strictly valid JSON object matching the requested schema. No markdown formatting outside the JSON, no explanations.
"""


def build_mock_screen_plan_prompt(brd_text: str, project_name: Optional[str] = "") -> str:
    normalized_brd = brd_text.strip()
    return f"""{MOCK_SCREEN_PLAN_SYSTEM_PROMPT}

Project Context: {project_name or 'Enterprise Initiative'}

FULL BUSINESS REQUIREMENTS DOCUMENT (BRD):
\"\"\"
{normalized_brd}
\"\"\"

Analyze the complete BRD above and produce the structured Screen Plan JSON object matching the following structure exactly:

{{
  "application_name": "Official or derived Name of the Application",
  "application_summary": "High-level summary of the application and its business purpose",
  "user_roles": ["Role 1", "Role 2", ...],
  "design_context": {{
    "application_type": "e.g. Retail Banking Portal, Enterprise Credit Platform, etc.",
    "design_style": "enterprise",
    "primary_color": "Hex color code e.g. #1E40AF or #0284C7",
    "secondary_color": "Hex color code e.g. #0D9488 or #475569",
    "accent_color": "Hex color code e.g. #F59E0B",
    "neutral_dark": "#0F172A",
    "neutral_light": "#F8FAFC",
    "surface_color": "#FFFFFF",
    "density": "comfortable",
    "navigation_pattern": "sidebar_and_header",
    "brand_name": "Company/System Brand"
  }},
  "screens": [
    {{
      "screen_id": "SCREEN-001",
      "sequence": 1,
      "name": "Screen Title",
      "purpose": "Precise business purpose of this screen according to the BRD",
      "user_role": "Primary user role interacting with this screen",
      "screen_type": "dashboard | search | work_queue | detail_view | create_form | approval | report | audit | login | etc.",
      "navigation_context": {{
        "active_nav_item": "Sidebar navigation item name",
        "navigation_items": ["Only navigation destinations supported by the BRD"],
        "breadcrumbs": ["Home", "Section", "Current Screen"]
      }},
      "header_stats": [],
      "components": [
        {{
          "type": "kpi_grid | table | form | filters | detail_card | workflow_stepper | alert_banner",
          "title": "Component Title",
          "description": "Optional description",
          "fields": [
            {{ "label": "Field Name", "type": "text|select|date|number|textarea", "value": "Sample Value", "placeholder": "Placeholder text", "required": true }}
          ],
          "columns": ["Col 1", "Col 2", "Status", "Actions"],
          "rows": [
            {{ "Col 1": "Val 1", "Col 2": "Val 2", "Status": "Active" }}
          ],
          "actions": [
            {{ "label": "Button Label", "type": "primary|secondary|danger", "icon": "check" }}
          ],
          "steps": ["Step 1", "Step 2", "Step 3"]
        }}
      ],
      "fields": [],
      "tables": [],
      "actions": [
        {{ "label": "Primary Page Action", "type": "primary", "target": "Next Screen" }}
      ],
      "workflow_state": "e.g. Draft / Pending Approval / Active",
      "business_rules": ["Rule 1 explicitly from BRD", "Rule 2"],
      "notifications": ["Notification alert text if applicable"],
      "data_sources": ["Entities/Tables affected"],
      "related_requirements": ["BR-01", "BR-02"]
    }}
  ]
}}

For each screen, choose components that support its own task and hierarchy. Use header_stats only when the screen is genuinely about monitoring or analysis; use steps for guided workflows; use fields for entry or record details; and use tables for actual searchable/triageable collections. Populate data only when grounded in the BRD, otherwise leave the corresponding arrays empty. Avoid copying the same component mix to adjacent screens.

Analyze the complete BRD above and derive the complete screen plan from all of its content.
Count all discernible features, entities, workflows, approval stages, and reports that require UI interaction.
Return every screen supported by the supplied source; do not omit later sections or requirements.
"""


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


MOCK_SCREEN_RENDER_BRIEF_TEMPLATE = """PyMuPDF static UI mockup for {brand_name} ({application_type}).
Screen {sequence}: {screen_name}. Purpose: {purpose}.
Role: {user_role}. Layout: {layout}.
Navigation: {navigation}. Fields: {fields}.
Table columns: {table_columns}. Actions: {actions}."""


def build_mock_screen_render_brief(
    *,
    brand_name: str,
    application_type: str,
    sequence: int,
    screen_name: str,
    purpose: str,
    user_role: str,
    layout: str,
    navigation: str,
    fields: str,
    table_columns: str,
    actions: str,
) -> str:
    return MOCK_SCREEN_RENDER_BRIEF_TEMPLATE.format(
        brand_name=brand_name,
        application_type=application_type,
        sequence=sequence,
        screen_name=screen_name,
        purpose=purpose,
        user_role=user_role,
        layout=layout,
        navigation=navigation,
        fields=fields,
        table_columns=table_columns,
        actions=actions,
    )