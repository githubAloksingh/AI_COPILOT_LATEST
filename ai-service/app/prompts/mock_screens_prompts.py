import json
from typing import Optional

from app.api.schemas import ScreenInteraction
from app.prompts.guardrails import GUARDRAILS

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
    interaction_schema = json.dumps(ScreenInteraction.model_json_schema(), indent=2)
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
  "global_navigation": {{
    "entry_screen": "SCREEN-001",
    "navigation_graph": [
      {{ "from_screen_id": "SCREEN-001", "to_screen_id": "SCREEN-002", "event": "EVT-LOGIN", "condition": "authenticated", "label": "On Login Success" }}
    ],
    "data_entities": ["Entity1", "Entity2"],
    "shared_workflows": [
      {{ "id": "WF-01", "name": "Primary Approval Workflow", "screens": ["SCREEN-002", "SCREEN-003"], "description": "Core lifecycle workflow" }}
    ]
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
          "chart_type": "pie | bar | line",
          "chart_data": [
            {{ "label": "Category or period", "value": 12 }}
          ],
          "chart_data_source": "brd | screen_data | illustrative",
          "chart_note": "Required when chart_data_source is illustrative; clearly say 'Illustrative data'",
          "chart_value_prefix": "Optional unit prefix, for example $",
          "chart_value_suffix": "Optional unit suffix, for example % or cases",
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
      "interaction": {{
        "events": [],
        "navigation_flows": [],
        "data_bindings": [],
        "validation_rules": []
      }},
      "workflow_state": "e.g. Draft / Pending Approval / Active",
      "business_rules": ["Rule 1 explicitly from BRD", "Rule 2"],
      "notifications": ["Notification alert text if applicable"],
      "data_sources": ["Entities/Tables affected"],
      "related_requirements": ["BR-01", "BR-02"]
    }}
  ]
}}

INTERACTION OBJECT JSON SCHEMA (authoritative; follow property names, required properties, and types exactly):
{interaction_schema}

For each screen, include an interaction object. Populate events, navigation_flows, data_bindings, and validation_rules only when supported by the BRD; use empty arrays when there are no applicable items. Every event item must be an object with a string "label"; use the exact property names in the schema (including snake_case). Every navigation_flows item must include string "from_event" and "to_screen_id". Every data_bindings item must include string "field" and "entity". Do not encode these objects as strings, rename properties, or omit required properties. Do not invent event, navigation, entity, field, or validation details merely to populate an array.

For each screen, choose components that support its own task and hierarchy. Use header_stats only when the screen is genuinely about monitoring or analysis; use steps for guided workflows; use fields for entry or record details; and use tables for actual searchable/triageable collections. Populate data only when grounded in the BRD, otherwise leave the corresponding arrays empty. Avoid copying the same component mix to adjacent screens.

For dashboard, analytics, or report screens, include a chart component only when the BRD supports the visualization. Set chart_type to pie for category proportions (at least two categories), bar for category comparisons (including positive/negative financial amounts), or line for values over time (at least two ordered points); provide chart_data as label/value objects. Values may come directly from the BRD or from explicit numeric values already included in the screen's BRD-derived stats, tables, or components; aggregate only when that aggregation directly represents a stated BRD metric. Set chart_data_source to "brd" when values are stated in the BRD and "screen_data" when values come from another explicit screen dataset. Use chart_value_prefix/suffix for units or currency specified by the BRD. Never present invented metrics as factual. Use "illustrative" only when the BRD requires or clearly supports the analysis but supplies no values and a sample visualization is necessary; in that case chart_note must clearly state "Illustrative data". Leave chart arrays empty when no relevant data or analytical requirement exists. Do not add charts to forms, login pages, or unrelated screens.

Analyze the complete BRD above and derive the complete screen plan from all of its content.
Count all discernible features, entities, workflows, approval stages, and reports that require UI interaction.
Return every screen supported by the supplied source; do not omit later sections or requirements.
"""


def build_screen_explanation_prompt(spec_dict: dict, brd_excerpt: Optional[str] = "", project_name: Optional[str] = "") -> str:
    import json
    spec_json = json.dumps(spec_dict, indent=2)
    return f"""You are a Principal Enterprise Systems Architect and UX Analyst.
Your task is to produce a comprehensive, structured, BRD-grounded explanation for the following screen specification.

PROJECT CONTEXT: {project_name or 'Enterprise Platform'}

SCREEN SPECIFICATION:
{spec_json}

RELEVANT BRD CONTEXT:
\"\"\"
{brd_excerpt[:15000] if brd_excerpt else 'Use the details within the screen specification directly.'}
\"\"\"

Produce a strictly valid JSON explanation matching this schema exactly:
{{
  "purpose_summary": "In-depth summary explaining the screen's operational purpose, target user personas, and where it fits in the broader business process.",
  "sections": [
    {{
      "title": "Section Name (e.g. Header, Primary Form, Item Grid, Decision Actions)",
      "description": "Functional description of what this section accomplishes.",
      "fields": [
        {{ "name": "Field Label", "type": "text|number|date|select", "required": true, "rule": "Validation or business rule applied" }}
      ],
      "columns": ["Col 1", "Col 2"],
      "notes": "Any special behaviors or UX considerations."
    }}
  ],
  "actions": [
    {{ "label": "Action Button Label", "type": "primary|secondary|danger", "outcome": "Detailed outcome of this action, including validations, persistence, and workflow state transitions." }}
  ],
  "validation_rules": [
    "Rule 1 explicitly grounded in BRD",
    "Rule 2"
  ],
  "navigation_flow": "Detailed explanation of navigation into this screen, transition conditions, and navigation destinations upon completion or cancellation.",
  "brd_references": ["BR-01", "Section 3.2", "Requirement ID"]
}}

CRITICAL RULES:
1. Ground all explanations in the specification and BRD. Do not invent unrelated business facts.
2. Provide clear, professional explanations suitable for inclusion in an executive architectural specification document.
3. Return valid JSON only with NO markdown wrapper, NO commentary outside the JSON object.
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