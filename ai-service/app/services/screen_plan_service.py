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

    def __init__(self, message: str, diagnostics: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.diagnostics = diagnostics or []


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
        previous_error: Optional[ScreenPlanValidationError] = None
        plan: Optional[ScreenPlan] = None
        for attempt in range(2):
            attempt_prompt = (
                prompt
                if previous_error is None
                else self._build_corrective_prompt(prompt, previous_error)
            )
            try:
                raw_json_dict = self.gemini.generate_dict(
                    attempt_prompt,
                    response_schema=self._gemini_response_schema(),
                    require_object=True,
                )
            except RuntimeError as exc:
                if "Invalid JSON from Gemini" not in str(exc):
                    raise
                logger.warning(
                    "Gemini returned malformed screen-plan JSON on attempt %d: %s",
                    attempt + 1,
                    exc,
                )
                previous_error = ScreenPlanValidationError(
                    "Gemini returned malformed JSON for the screen plan."
                )
                if attempt == 0:
                    continue
                raise previous_error from exc

            try:
                raw_json_dict = self._normalize_plan_response(raw_json_dict)
                screen_count = len(raw_json_dict.get("screens", [])) if isinstance(raw_json_dict, dict) else 0
                logger.info(
                    "Parsed Gemini screen-plan response: top_level_keys=%s screen_count=%d",
                    sorted(raw_json_dict.keys()) if isinstance(raw_json_dict, dict) else [],
                    screen_count,
                )
                plan = self._parse_and_validate_plan(
                    raw_json_dict,
                    project_name=project_name,
                    source_content_truncated=source_content_truncated,
                    source_character_count=source_character_count,
                    analyzed_character_count=analyzed_character_count,
                )
                break
            except ScreenPlanValidationError as exc:
                previous_error = exc
                logger.warning(
                    "Gemini screen-plan validation failed on attempt %d: %s",
                    attempt + 1,
                    exc,
                )
                if attempt == 1:
                    raise

        if plan is None:
            raise ScreenPlanValidationError("Gemini failed to produce a valid screen plan after one correction retry.")
        
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
        source_text: Optional[str] = None,
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
            self._validate_evidenced_fields(
                screen_data,
                source_text=source_text,
                screen_number=idx,
            )
            try:
                validated_spec = ScreenSpecification.model_validate(screen_data)
            except ValidationError as exc:
                diagnostics = self._validation_diagnostics(
                    exc.errors(),
                    prefix=("screens", idx - 1),
                )
                self._log_validation_diagnostics(diagnostics)
                errors = "; ".join(
                    f"{item['path']}: {item['expected_type']} expected; received {item['received']}"
                    for item in diagnostics
                )
                raise ScreenPlanValidationError(
                    f"Screen {idx} is invalid: {errors}",
                    diagnostics=diagnostics,
                ) from exc

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
            diagnostics = self._validation_diagnostics(exc.errors())
            self._log_validation_diagnostics(diagnostics)
            errors = "; ".join(
                f"{item['path']}: {item['expected_type']} expected; received {item['received']}"
                for item in diagnostics
            )
            raise ScreenPlanValidationError(
                f"Screen plan is invalid: {errors}",
                diagnostics=diagnostics,
            ) from exc

        if not plan.application_summary.strip():
            raise ScreenPlanValidationError("Screen plan application_summary is required.")
        if source_content_truncated:
            plan.application_summary = (
                f"{plan.application_summary.rstrip()} "
                "This plan is based on a truncated BRD excerpt; omitted content was not analyzed."
            )
        return plan

    @classmethod
    def _validate_evidenced_fields(
        cls,
        screen_data: Dict[str, Any],
        source_text: Optional[str],
        screen_number: int,
    ) -> None:
        evidence = screen_data.get("source_evidence")
        evidence_text = (
            "\n".join(item for item in evidence if isinstance(item, str))
            if isinstance(evidence, list)
            else evidence if isinstance(evidence, str) else ""
        )
        source = evidence_text or source_text or ""
        expected_fields = cls._extract_explicit_field_labels(source)
        if not expected_fields:
            return

        raw_fields = screen_data.get("fields")
        present_fields = {
            cls._normalize_field_label(field.get("label"))
            for field in raw_fields if isinstance(field, dict)
            if isinstance(field.get("label"), str)
        } if isinstance(raw_fields, list) else set()
        components = screen_data.get("components")
        for component in components if isinstance(components, list) else []:
            component_fields = component.get("fields") if isinstance(component, dict) else None
            if isinstance(component_fields, list):
                present_fields.update(
                    cls._normalize_field_label(field.get("label"))
                    for field in component_fields
                    if isinstance(field, dict) and isinstance(field.get("label"), str)
                )

        missing = [label for label in expected_fields if cls._normalize_field_label(label) not in present_fields]
        if missing:
            raise ScreenPlanValidationError(
                f"Screen {screen_number} is missing required screen_fields "
                + ", ".join(f"'{label}'" for label in missing)
                + "."
            )

    @staticmethod
    def _extract_explicit_field_labels(source: str) -> List[str]:
        labels = []
        pattern = re.compile(
            r"\b(?:with|and|include|including|contain|containing)\s+"
            r"(?:a|an|the)?\s*([A-Za-z0-9][A-Za-z0-9 _/()'-]*?)\s+"
            r"(?:field|checkbox|input)\b",
            re.IGNORECASE,
        )
        for match in pattern.finditer(source):
            label = match.group(1).strip(" \t\r\n.,;:-")
            if label and label.casefold() not in {item.casefold() for item in labels}:
                labels.append(label)
        return labels

    @staticmethod
    def _normalize_field_label(label: Optional[str]) -> str:
        return re.sub(r"\s+", " ", label or "").strip().casefold()

    def _build_corrective_prompt(
        self,
        original_prompt: str,
        previous_error: ScreenPlanValidationError,
    ) -> str:
        if previous_error.diagnostics:
            feedback = "\n".join(
                f'- {item["path"]}: expected {item["expected_type"]}; '
                f'received {item["received"]}'
                for item in previous_error.diagnostics
            )
        else:
            feedback = str(previous_error)
        return (
            f"{original_prompt}\n\n"
            "CORRECTIVE RETRY: Your previous screen-plan response failed validation. "
            "Return the complete corrected plan JSON object, preserving all valid BRD-derived "
            "screens, sequence numbers, requirements, and interactions. Correct every issue "
            "listed below. Follow the authoritative interaction JSON schema in the prompt; "
            "do not remove a BRD-supported event, flow, or binding to avoid validation.\n"
            f"Validation diagnostics:\n{feedback}"
        )

    @staticmethod
    def _normalize_plan_response(data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ScreenPlanValidationError(
                f"Gemini screen-plan response must be an object; received {type(data).__name__}."
            )

        payload = data
        screen_keys = ("screens", "screenSpecifications", "screen_specifications", "mockScreens", "mock_screens")
        for wrapper in ("plan", "screenPlan", "screen_plan", "data"):
            nested = payload.get(wrapper)
            if isinstance(nested, dict) and any(key in nested for key in screen_keys):
                payload = nested
                logger.warning("Unwrapped Gemini screen-plan response from '%s'.", wrapper)
                break

        normalized = dict(payload)
        aliases = {
            "applicationName": "application_name",
            "applicationSummary": "application_summary",
            "userRoles": "user_roles",
            "designContext": "design_context",
            "globalNavigation": "global_navigation",
            "screenSpecifications": "screens",
            "screen_specifications": "screens",
            "mockScreens": "screens",
            "mock_screens": "screens",
        }
        for source, target in aliases.items():
            if target not in normalized and source in normalized:
                normalized[target] = normalized.pop(source)
                logger.info("Mapped Gemini response property '%s' to '%s'.", source, target)

        screens = normalized.get("screens")
        if isinstance(screens, list):
            normalized["screens"] = [
                ScreenPlanService._normalize_screen_properties(screen)
                if isinstance(screen, dict)
                else screen
                for screen in screens
            ]
        return normalized

    @staticmethod
    def _normalize_screen_properties(screen: Dict[str, Any]) -> Dict[str, Any]:
        aliases = {
            "screenId": "screen_id",
            "screenType": "screen_type",
            "userRole": "user_role",
            "navigationContext": "navigation_context",
            "headerStats": "header_stats",
            "businessRules": "business_rules",
            "dataSources": "data_sources",
            "relatedRequirements": "related_requirements",
            "workflowState": "workflow_state",
        }
        normalized = dict(screen)
        for source, target in aliases.items():
            if target not in normalized and source in normalized:
                normalized[target] = normalized.pop(source)

        navigation = normalized.get("navigation_context")
        if isinstance(navigation, dict):
            normalized["navigation_context"] = {
                {"activeNavItem": "active_nav_item", "navigationItems": "navigation_items"}.get(key, key): value
                for key, value in navigation.items()
            }

        interaction = normalized.get("interaction")
        if isinstance(interaction, dict):
            interaction_aliases = {
                "navigationFlows": "navigation_flows",
                "dataBindings": "data_bindings",
                "validationRules": "validation_rules",
            }
            interaction = {
                interaction_aliases.get(key, key): value
                for key, value in interaction.items()
            }
            for collection, item_aliases in (
                ("events", {"triggerComponent": "trigger_component", "businessRuleRefs": "business_rule_refs"}),
                ("navigation_flows", {"fromEvent": "from_event", "toScreenId": "to_screen_id"}),
                ("data_bindings", {"bindingType": "binding_type"}),
            ):
                items = interaction.get(collection)
                if isinstance(items, list):
                    interaction[collection] = [
                        {
                            item_aliases.get(key, key): value
                            for key, value in item.items()
                        } if isinstance(item, dict) else item
                        for item in items
                    ]
            normalized["interaction"] = interaction
        components = normalized.get("components")
        if isinstance(components, list):
            component_aliases = {
                "chartType": "chart_type",
                "chartData": "chart_data",
                "chartNote": "chart_note",
                "chartDataSource": "chart_data_source",
                "chartValuePrefix": "chart_value_prefix",
                "chartValueSuffix": "chart_value_suffix",
                "progressValue": "progress_value",
                "progressLabel": "progress_label",
                "progressDataSource": "progress_data_source",
                "progressNote": "progress_note",
            }
            normalized["components"] = [
                {
                    component_aliases.get(key, key): value
                    for key, value in component.items()
                } if isinstance(component, dict) else component
                for component in components
            ]
        return normalized

    @classmethod
    def _gemini_response_schema(cls) -> Dict[str, Any]:
        schema = ScreenPlan.model_json_schema()
        definitions = schema.get("$defs", {})

        def inline_references(value: Any, stack: tuple = ()) -> Any:
            if isinstance(value, list):
                return [inline_references(item, stack) for item in value]
            if not isinstance(value, dict):
                return value

            reference = value.get("$ref")
            if reference:
                definition_name = reference.rsplit("/", 1)[-1]
                if definition_name in stack or definition_name not in definitions:
                    raise ScreenPlanValidationError(
                        f"Unsupported recursive or unresolved Gemini schema reference: {reference}"
                    )
                resolved = inline_references(
                    definitions[definition_name],
                    (*stack, definition_name),
                )
                siblings = {
                    key: item
                    for key, item in value.items()
                    if key != "$ref"
                }
                resolved.update(inline_references(siblings, stack))
                return resolved

            return {
                key: inline_references(item, stack)
                for key, item in value.items()
                if key not in {"title", "default", "$defs"}
            }

        schema = inline_references(schema)
        schema["required"] = list(dict.fromkeys(
            [*schema.get("required", []), "application_name", "application_summary", "screens"]
        ))
        screen_items = schema["properties"]["screens"]["items"]
        screen_items["required"] = list(dict.fromkeys(
            [*screen_items.get("required", []), "name", "purpose", "interaction"]
        ))
        schema["properties"]["screens"]["minItems"] = 1

        interaction_schema = screen_items["properties"]["interaction"]
        interaction_object = next(
            option for option in interaction_schema.get("anyOf", [])
            if option.get("type") == "object"
        )
        interaction_schema.clear()
        interaction_schema.update(interaction_object)
        interaction_schema["required"] = [
            "events",
            "navigation_flows",
            "data_bindings",
            "validation_rules",
        ]
        return schema

    def _validation_diagnostics(
        self,
        errors: List[Dict[str, Any]],
        prefix: tuple = (),
    ) -> List[Dict[str, str]]:
        diagnostics = []
        expected_types = {
            "id": "string",
            "type": "string",
            "label": "string",
            "trigger_component": "string or null",
            "business_rule_refs": "array of strings",
            "from_event": "string",
            "to_screen_id": "string",
            "condition": "string or null",
            "field": "string",
            "entity": "string",
            "attribute": "string or null",
            "binding_type": "string or null",
        }
        for error in errors:
            path_parts = (*prefix, *error.get("loc", ()))
            path = ".".join(str(part) for part in path_parts)
            field_name = str(path_parts[-1]) if path_parts else "value"
            received = "<missing>" if error.get("type") == "missing" else repr(error.get("input"))
            diagnostics.append({
                "path": path,
                "expected_type": expected_types.get(
                    field_name,
                    error.get("msg", "valid value"),
                ),
                "received": received,
            })
        return diagnostics

    @staticmethod
    def _log_validation_diagnostics(diagnostics: List[Dict[str, str]]) -> None:
        for item in diagnostics:
            logger.error(
                "Screen-plan validation error path=%s expected_type=%s received=%s",
                item["path"],
                item["expected_type"],
                item["received"],
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
                {"label": a.label, "type": a.type, "outcome": ""}
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
            navigation_flows = (
                [
                    f"{flow.label or flow.from_event} → {flow.to_screen_id}"
                    + (f" when {flow.condition}" if flow.condition else "")
                    for flow in spec.interaction.navigation_flows
                ]
                if spec.interaction
                else []
            )
            return ScreenExplanation(
                purpose_summary=spec.purpose,
                sections=sections,
                actions=actions_summary,
                validation_rules=spec.business_rules
                + (spec.interaction.validation_rules if spec.interaction else []),
                navigation_flow="; ".join(navigation_flows),
                brd_references=spec.related_requirements,
            )

screen_plan_service = ScreenPlanService()
