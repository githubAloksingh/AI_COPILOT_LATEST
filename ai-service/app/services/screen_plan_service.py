import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError
from app.api.schemas import (
    DesignContext,
    ScreenExplanation,
    ScreenPlan,
    ScreenSpecification,
)
from app.prompts.mock_screens_prompts import (
    build_mock_screen_plan_prompt,
    build_screen_explanation_prompt,
)
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class ScreenPlanValidationError(ValueError):
    """Raised when Gemini output cannot form a usable screen plan."""

class ScreenPlanService:
    def __init__(self):
        self.gemini = gemini_service

    def build_planning_prompt(self, brd_text: str, project_name: Optional[str] = "") -> str:
        return build_mock_screen_plan_prompt(brd_text, project_name)

    def generate_plan(self, brd_text: str, project_name: Optional[str] = "") -> ScreenPlan:
        normalized_brd = brd_text.strip() if brd_text else ""
        if not normalized_brd:
            raise ScreenPlanValidationError("BRD text is empty; a screen plan cannot be generated.")

        source_character_count = len(normalized_brd)
        analyzed_character_count = source_character_count
        source_content_truncated = False
        start_time = time.time()
        logger.info(
            "Starting Gemini screen-plan analysis: source_characters=%d",
            source_character_count,
        )
        
        prompt = self.build_planning_prompt(normalized_brd, project_name)
        try:
            raw_json_dict = self.gemini.generate_dict(prompt)
        except RuntimeError as exc:
            if "Invalid JSON from Gemini" in str(exc):
                raise ScreenPlanValidationError(
                    "Gemini returned malformed JSON for the screen plan."
                ) from exc
            raise
        
        # Validate and normalize into ScreenPlan model
        plan = self._parse_and_validate_plan(
            raw_json_dict,
            project_name=project_name,
            source_content_truncated=source_content_truncated,
            source_character_count=source_character_count,
            analyzed_character_count=analyzed_character_count,
        )
        
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
        project_name: Optional[str] = "",
        source_content_truncated: bool = False,
        source_character_count: int = 0,
        analyzed_character_count: int = 0,
    ) -> ScreenPlan:
        """Validate planner output against the screen-plan Pydantic schemas."""
        if not isinstance(data, dict):
            raise ScreenPlanValidationError("Gemini screen-plan response must be a JSON object.")
        if not isinstance(data.get("screens"), list) or not data["screens"]:
            raise ScreenPlanValidationError(
                "Gemini screen plan contains no screens; refusing to substitute a generic screen."
            )

        # Parse design context
        dc_data = data.get("design_context") or {}
        if not isinstance(dc_data, dict):
            raise ScreenPlanValidationError("Screen plan design_context must be a JSON object.")
        app_name = data.get("application_name")
        if not isinstance(app_name, str) or not app_name.strip():
            raise ScreenPlanValidationError("Screen plan application_name is required.")
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

        validated_screens: List[ScreenSpecification] = []
        seen_ids = set()
        seen_sequences = set()

        for idx, s in enumerate(data["screens"], start=1):
            if not isinstance(s, dict):
                raise ScreenPlanValidationError(f"Screen {idx} must be a JSON object.")

            screen_name = s.get("name")
            purpose = s.get("purpose")
            if not isinstance(screen_name, str) or not screen_name.strip():
                raise ScreenPlanValidationError(f"Screen {idx} is missing required property 'name'.")
            if not isinstance(purpose, str) or not purpose.strip():
                raise ScreenPlanValidationError(f"Screen {idx} is missing required property 'purpose'.")

            screen_data = dict(s)
            screen_data.setdefault("screen_id", f"SCREEN-{idx:03d}")
            screen_data.setdefault("sequence", idx)
            screen_data.setdefault("screen_type", self._infer_screen_type(screen_name))
            screen_data.setdefault(
                "navigation_context",
                {"active_nav_item": screen_name, "breadcrumbs": [app_name, screen_name]},
            )
            try:
                validated_spec = ScreenSpecification.model_validate(screen_data)
            except ValidationError as exc:
                errors = "; ".join(
                    f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                    for error in exc.errors(include_input=False)
                )
                raise ScreenPlanValidationError(f"Screen {idx} is invalid: {errors}") from exc

            if validated_spec.screen_id in seen_ids:
                raise ScreenPlanValidationError(
                    f"Screen {idx} has duplicate screen_id '{validated_spec.screen_id}'."
                )
            if validated_spec.sequence < 1:
                raise ScreenPlanValidationError(
                    f"Screen {idx} sequence must be a positive integer."
                )
            if validated_spec.sequence in seen_sequences:
                raise ScreenPlanValidationError(
                    f"Screen plan has duplicate sequence {validated_spec.sequence}."
                )
            seen_ids.add(validated_spec.screen_id)
            seen_sequences.add(validated_spec.sequence)
            validated_screens.append(validated_spec)

        validated_screens.sort(key=lambda x: x.sequence)
        navigation_items = []
        for screen in validated_screens:
            nav_context = screen.navigation_context
            label = nav_context.get("active_nav_item") if isinstance(nav_context, dict) else None
            label = label if isinstance(label, str) and label.strip() else screen.name
            if label not in navigation_items:
                navigation_items.append(label)
        for i, sc in enumerate(validated_screens, start=1):
            sc.sequence = i
            if isinstance(sc.navigation_context, dict):
                sc.navigation_context.setdefault("navigation_items", navigation_items)

        plan_data = dict(data)
        plan_data.update({
            "application_name": app_name,
            "design_context": design_context,
            "screens": validated_screens,
            "source_content_truncated": source_content_truncated,
            "source_character_count": source_character_count,
            "analyzed_character_count": analyzed_character_count,
        })
        try:
            plan = ScreenPlan.model_validate(plan_data)
        except ValidationError as exc:
            errors = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors(include_input=False)
            )
            raise ScreenPlanValidationError(f"Screen plan is invalid: {errors}") from exc

        if not plan.application_summary.strip():
            raise ScreenPlanValidationError("Screen plan application_summary is required.")
        if source_content_truncated:
            plan.application_summary = (
                f"{plan.application_summary.rstrip()} "
                "This plan is based on a truncated BRD excerpt; omitted content was not analyzed."
            )
        return plan

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

    def generate_screen_explanation(
        self,
        spec: ScreenSpecification,
        brd_excerpt: Optional[str] = "",
        project_name: Optional[str] = "",
    ) -> ScreenExplanation:
        """
        Generates a comprehensive, BRD-grounded architectural explanation for a single screen.
        """
        prompt = build_screen_explanation_prompt(spec.model_dump(), brd_excerpt, project_name)
        try:
            raw_dict = self.gemini.generate_dict(prompt)
            return ScreenExplanation.model_validate(raw_dict)
        except Exception as exc:
            logger.warning("Gemini explanation generation failed or returned invalid schema for screen %s: %s", spec.name, exc)
            # Safe grounded fallback from the screen specification itself
            fields_summary = [
                {"name": f.label, "type": f.type, "required": f.required, "rule": f.placeholder or ""}
                for f in spec.fields[:10]
            ]
            actions_summary = [
                {"label": a.label, "type": a.type, "outcome": f"Triggers {a.label} action on {spec.name}"}
                for a in spec.actions
            ]
            sections = [
                {
                    "title": "Primary Screen Content",
                    "description": f"Contains core user interface components for {spec.name}.",
                    "fields": fields_summary,
                    "columns": [c for t in spec.tables for c in t.columns[:5]],
                    "notes": spec.purpose,
                }
            ]
            return ScreenExplanation(
                purpose_summary=spec.purpose,
                sections=sections,
                actions=actions_summary,
                validation_rules=spec.business_rules if spec.business_rules else ["Input validation per system standards."],
                navigation_flow=f"Accessible by {spec.user_role} within the {spec.screen_type} workflow.",
                brd_references=spec.related_requirements if spec.related_requirements else ["BRD Requirement Baseline"],
            )

screen_plan_service = ScreenPlanService()
