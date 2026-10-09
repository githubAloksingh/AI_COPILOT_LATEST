import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from app.api.schemas import (
    DesignContext,
    ScreenAction,
    ScreenComponent,
    ScreenField,
    ScreenPlan,
    ScreenSpecification,
    ScreenTable,
    HeaderStat
)
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

MOCK_SCREEN_PLAN_SYSTEM_PROMPT = """You are a Senior Product Architect, UX Architect, and Principal Business Analyst specializing in enterprise application systems.

Your objective is to read a COMPLETE Business Requirements Document (BRD) and architect the exact, comprehensive UI screen flow, specifications, and design system required to build the real enterprise application.

CRITICAL RULES:
1. GROUNDED IN BRD: Derive all application features, entities, workflows, screens, fields, tables, actions, and validation rules directly from the BRD content.
2. DYNAMIC SCREEN DISCOVERY: DO NOT assume a fixed list of screens or fixed screen count. Different BRDs have completely different screen counts, journeys, and purposes. A typical enterprise BRD produces 12-25 screens. A complex BRD may require 30+. DO NOT stop at 7 or 8 screens.
3. EXHAUSTIVE COVERAGE: Every distinct feature, workflow, entity lifecycle, approval step, report, and configuration panel mentioned in the BRD must have a corresponding screen. DO NOT skip or merge screens to shorten the output.
4. LOGICAL USER JOURNEY: Determine the natural, logical progression from initial entry/login to main working queues, detail forms, approval checkpoints, settlements, reports, and audit trails as mandated by the BRD.
5. SCREEN TYPES: Choose realistic enterprise screen types appropriate for each requirement (e.g., login, dashboard, work_queue, detail_view, create_form, edit_form, approval_checkpoint, workflow_stepper, adhoc_report, audit_trail, document_viewer, configuration, error_exception).
6. TASK-SPECIFIC CONTENT: Include only fields, tables, metrics, actions, statuses, and rules that serve the screen's BRD-defined task. Do not force KPI tiles, tables, or forms onto every screen and do not invent sample business facts.
7. DESIGN SYSTEM: Formulate a cohesive enterprise color palette and visual design context that reflects the business domain (e.g. Banking, Healthcare, Supply Chain, Insurance).
8. DISTINCT COMPOSITION: Assign each screen a screen_type that accurately expresses its user task. Use overview layouts for monitoring, work queues for triage, focused forms for data entry, split case workspaces for record review, document-review layouts for document inspection, report layouts for analysis, and decision panels for approvals. Screens in one application share their visual identity, not an identical content structure.
9. COMPLETE JSON OUTPUT: You MUST output the complete JSON. Do NOT truncate, do NOT stop mid-array, do NOT summarize remaining screens. The JSON must contain all screens from screen 1 to the last screen. If you are about to run out of space, write shorter but still include EVERY screen.
10. RETURN VALID JSON ONLY: Return a single strictly valid JSON object matching the requested schema. No markdown formatting outside the JSON, no explanations.
"""


class ScreenPlanService:
    def __init__(self):
        self.gemini = gemini_service

    def build_planning_prompt(self, brd_text: str, project_name: Optional[str] = "") -> str:
        truncated_brd = brd_text.strip()
        # Ensure we send comprehensive BRD content while remaining safely within token limits
        if len(truncated_brd) > 180000:
            truncated_brd = truncated_brd[:180000] + "\n\n...[Content truncated for analysis length]..."

        return f"""{MOCK_SCREEN_PLAN_SYSTEM_PROMPT}

Project Context: {project_name or 'Enterprise Initiative'}

FULL BUSINESS REQUIREMENTS DOCUMENT (BRD):
\"\"\"
{truncated_brd}
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

Generate the COMPLETE, unhurried, exhaustive list of ALL screens required by this BRD.
IMPORTANT: You MUST include EVERY screen. DO NOT stop early. DO NOT truncate the array.
Count all features, entities, workflows, approval stages, and reports in the BRD — each one that requires UI interaction MUST become a screen.
Output the full JSON array with all screens. A typical BRD requires 12-25 screens or more.
"""

    def generate_plan(self, brd_text: str, project_name: Optional[str] = "") -> ScreenPlan:
        start_time = time.time()
        logger.info("Starting Gemini Screen Plan analysis for BRD (%d characters)...", len(brd_text))
        
        prompt = self.build_planning_prompt(brd_text, project_name)
        raw_json_dict = self.gemini.generate_dict(prompt)
        
        # Validate and normalize into ScreenPlan model
        plan = self._parse_and_validate_plan(raw_json_dict, brd_text, project_name)
        
        duration = int((time.time() - start_time) * 1000)
        logger.info(
            "Screen Plan generation completed successfully in %d ms with %d dynamic screens: %s",
            duration,
            len(plan.screens),
            [s.name for s in plan.screens]
        )
        return plan

    def _parse_and_validate_plan(
        self,
        data: Dict[str, Any],
        brd_text: str,
        project_name: Optional[str] = ""
    ) -> ScreenPlan:
        """Section 25: Comprehensive Validation of Screen Plan."""
        # Check root fields
        app_name = data.get("application_name") or project_name or "Enterprise Solution"
        app_summary = data.get("application_summary") or "Comprehensive enterprise application system derived from BRD."
        user_roles = data.get("user_roles") or ["Enterprise User"]
        
        # Parse design context
        dc_data = data.get("design_context") or {}
        design_context = DesignContext(
            application_type=dc_data.get("application_type") or "Enterprise Web Application",
            design_style=dc_data.get("design_style") or "enterprise",
            primary_color=self._sanitize_hex(dc_data.get("primary_color"), "#1E40AF"),
            secondary_color=self._sanitize_hex(dc_data.get("secondary_color"), "#0D9488"),
            accent_color=self._sanitize_hex(dc_data.get("accent_color"), "#F59E0B"),
            neutral_dark=self._sanitize_hex(dc_data.get("neutral_dark"), "#0F172A"),
            neutral_light=self._sanitize_hex(dc_data.get("neutral_light"), "#F8FAFC"),
            surface_color=self._sanitize_hex(dc_data.get("surface_color"), "#FFFFFF"),
            density=dc_data.get("density") or "comfortable",
            navigation_pattern=dc_data.get("navigation_pattern") or "sidebar_and_header",
            brand_name=dc_data.get("brand_name") or app_name
        )

        screens_raw = data.get("screens") or []
        if not isinstance(screens_raw, list) or len(screens_raw) == 0:
            logger.warning("Screen list is empty from raw Gemini output. Attempting recovery parsing...")
            screens_raw = self._extract_fallback_screens_from_dict(data)

        # Validation Rule 1: At least one screen exists
        if not screens_raw:
            screens_raw = [
                {
                    "screen_id": "SCREEN-001",
                    "sequence": 1,
                    "name": "Dashboard",
                    "purpose": "Overview of operational activities and summaries",
                    "user_role": user_roles[0] if user_roles else "User",
                    "screen_type": "dashboard",
                    "components": []
                }
            ]

        validated_screens: List[ScreenSpecification] = []
        seen_ids = set()

        for idx, s in enumerate(screens_raw, start=1):
            if not isinstance(s, dict):
                continue
            
            # Sequence validation
            seq = s.get("sequence") or idx
            
            # Screen ID validation: ensure unique, non-duplicate
            raw_id = s.get("screen_id") or f"SCREEN-{seq:03d}"
            if raw_id in seen_ids:
                raw_id = f"SCREEN-{seq:03d}"
            seen_ids.add(raw_id)

            screen_name = s.get("name") or s.get("title") or f"Screen {seq}"
            purpose = s.get("purpose") or f"View and manage {screen_name} operations"
            user_role = s.get("user_role") or (user_roles[0] if user_roles else "Enterprise User")
            screen_type = s.get("screen_type") or self._infer_screen_type(screen_name)

            # Components validation
            components = []
            for c in s.get("components", []):
                if isinstance(c, dict):
                    components.append(ScreenComponent(
                        type=c.get("type", "detail_card"),
                        title=c.get("title", ""),
                        description=c.get("description", ""),
                        fields=[ScreenField(**f) for f in c.get("fields", []) if isinstance(f, dict)],
                        columns=c.get("columns", []) if isinstance(c.get("columns"), list) else [],
                        rows=c.get("rows", []) if isinstance(c.get("rows"), list) else [],
                        stats=[HeaderStat(**st) for st in c.get("stats", []) if isinstance(st, dict)],
                        actions=[ScreenAction(**a) for a in c.get("actions", []) if isinstance(a, dict)],
                        steps=c.get("steps", []) if isinstance(c.get("steps"), list) else []
                    ))

            # Header stats validation
            header_stats = []
            for st in s.get("header_stats", []):
                if isinstance(st, dict) and "label" in st and "value" in st:
                    header_stats.append(HeaderStat(
                        label=str(st.get("label", "")),
                        value=str(st.get("value", "")),
                        change=st.get("change"),
                        status=st.get("status", "normal")
                    ))

            # Actions validation
            actions = []
            for a in s.get("actions", []):
                if isinstance(a, dict) and "label" in a:
                    actions.append(ScreenAction(
                        label=str(a.get("label", "")),
                        type=a.get("type", "primary"),
                        icon=a.get("icon", ""),
                        target=a.get("target", "")
                    ))

            # Fields validation
            fields = []
            for f in s.get("fields", []):
                if isinstance(f, dict) and "label" in f:
                    fields.append(ScreenField(**f))

            # Tables validation
            tables = []
            for t in s.get("tables", []):
                if isinstance(t, dict):
                    tables.append(ScreenTable(**t))

            validated_spec = ScreenSpecification(
                screen_id=raw_id,
                sequence=seq,
                name=screen_name,
                purpose=purpose,
                user_role=user_role,
                screen_type=screen_type,
                navigation_context=s.get("navigation_context") or {"active_nav_item": screen_name, "breadcrumbs": [app_name, screen_name]},
                header_stats=header_stats,
                components=components,
                fields=fields,
                tables=tables,
                actions=actions,
                workflow_state=s.get("workflow_state", ""),
                business_rules=s.get("business_rules", []) if isinstance(s.get("business_rules"), list) else [],
                notifications=s.get("notifications", []) if isinstance(s.get("notifications"), list) else [],
                data_sources=s.get("data_sources", []) if isinstance(s.get("data_sources"), list) else [],
                related_requirements=s.get("related_requirements", []) if isinstance(s.get("related_requirements"), list) else []
            )
            validated_screens.append(validated_spec)

        # Sort strictly by sequence
        validated_screens.sort(key=lambda x: x.sequence)
        # Re-number sequence sequentially if gaps existed
        for i, sc in enumerate(validated_screens, start=1):
            sc.sequence = i

        return ScreenPlan(
            application_name=app_name,
            application_summary=app_summary,
            user_roles=user_roles,
            design_context=design_context,
            screens=validated_screens
        )

    def _sanitize_hex(self, color: Any, default: str) -> str:
        if isinstance(color, str) and re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", color.strip()):
            return color.strip()
        return default

    def _infer_screen_type(self, name: str) -> str:
        lower = name.lower()
        if "login" in lower or "auth" in lower:
            return "login"
        if "dash" in lower or "overview" in lower:
            return "dashboard"
        if "approval" in lower or "review" in lower:
            return "approval"
        if "report" in lower or "analytics" in lower:
            return "report"
        if "audit" in lower or "history" in lower or "log" in lower:
            return "audit"
        if "create" in lower or "new" in lower or "add" in lower or "form" in lower:
            return "create_form"
        if "list" in lower or "queue" in lower or "tracker" in lower or "search" in lower:
            return "work_queue"
        return "detail_view"

    def _extract_fallback_screens_from_dict(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and ("name" in v[0] or "title" in v[0]):
                return v
        return []


screen_plan_service = ScreenPlanService()
