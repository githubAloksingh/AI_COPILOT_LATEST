import base64
import io

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes import get_document_content
from app.api.schemas import DataBinding, NavigationFlow, ScreenComponent, ScreenEvent, ScreenInteraction
from app.main import app
from app.services.gemini_service import GeminiService
from app.services.retrieval_service import RetrievalService
from app.services.screen_plan_service import (
    ScreenPlanService,
    ScreenPlanValidationError,
)


client = TestClient(app)


def _valid_plan_data():
    return {
        "application_name": "Claims Portal",
        "application_summary": "Manage submitted claims.",
        "screens": [
            {
                "screen_id": "SCREEN-001",
                "sequence": 1,
                "name": "Claims Queue",
                "purpose": "Review submitted claims.",
                "components": [
                    {
                        "type": "table",
                        "title": "Open claims",
                        "columns": ["Claim ID", "Status"],
                        "fields": [{"label": "Claim status", "type": "select"}],
                    }
                ],
            }
        ],
    }


def test_document_content_endpoint_uses_ordered_document_context(monkeypatch):
    ordered_chunks = ["first chunk", "second chunk", "third chunk"]

    def retrieve_document_context(document_id):
        assert document_id == "42"
        return ordered_chunks, []

    monkeypatch.setattr(
        "app.api.routes.retrieval_service.retrieve_document_context",
        retrieve_document_context,
    )

    response = get_document_content("42")

    assert response["chunks"] == ordered_chunks
    assert response["content"] == "\n\n".join(ordered_chunks)


def test_document_context_sorts_chunks_by_ingestion_metadata(monkeypatch):
    class FakeCollection:
        def get(self, where, include):
            assert where == {"documentId": "42"}
            assert include == ["documents", "metadatas"]
            return {
                "documents": ["third", "first", "second"],
                "metadatas": [
                    {"documentId": "42", "fileName": "brd.pdf", "chunkIndex": 2},
                    {"documentId": "42", "fileName": "brd.pdf", "chunkIndex": 0},
                    {"documentId": "42", "fileName": "brd.pdf", "chunkIndex": 1},
                ],
            }

    service = RetrievalService()
    monkeypatch.setattr(service, "ensure_collection", lambda: None)
    monkeypatch.setattr(service, "_get_local_collection", lambda: FakeCollection())
    service._use_local = True

    chunks, sources = service.retrieve_document_context("42")

    assert chunks == ["first", "second", "third"]
    assert [source.chunk_index for source in sources] == [0, 1, 2]


def test_document_context_rejects_missing_chunk_order_metadata(monkeypatch):
    class FakeCollection:
        def get(self, where, include):
            return {
                "documents": ["first", "second"],
                "metadatas": [
                    {"documentId": "42", "chunkIndex": 0},
                    {"documentId": "42"},
                ],
            }

    service = RetrievalService()
    monkeypatch.setattr(service, "ensure_collection", lambda: None)
    monkeypatch.setattr(service, "_get_local_collection", lambda: FakeCollection())
    service._use_local = True

    with pytest.raises(RuntimeError, match="missing chunkIndex metadata"):
        service.retrieve_document_context("42")


def test_malformed_gemini_json_becomes_clear_screen_plan_validation_error(monkeypatch):
    service = ScreenPlanService()
    monkeypatch.setattr(
        service.gemini,
        "generate_dict",
        lambda prompt, response_schema=None, require_object=False: (_ for _ in ()).throw(
            RuntimeError("Invalid JSON from Gemini: malformed response")
        ),
    )

    with pytest.raises(ScreenPlanValidationError, match="Gemini returned malformed JSON"):
        service.generate_plan("Requirements text")


def test_empty_screen_plan_is_rejected_without_dashboard_fallback():
    service = ScreenPlanService()
    plan_data = _valid_plan_data()
    plan_data["screens"] = []

    with pytest.raises(ScreenPlanValidationError, match="contains no screens"):
        service._parse_and_validate_plan(plan_data)


def test_gemini_chart_provenance_and_units_are_normalized():
    normalized = ScreenPlanService._normalize_screen_properties({
        "name": "Cash flow",
        "components": [{
            "type": "chart",
            "chartType": "bar",
            "chartData": [{"label": "Operating cost", "value": 25}],
            "chartDataSource": "brd",
            "chartValuePrefix": "$",
        }],
    })

    chart = ScreenComponent.model_validate(normalized["components"][0])
    assert chart.chart_type == "bar"
    assert chart.chart_data_source == "brd"
    assert chart.chart_value_prefix == "$"


def test_interaction_models_accept_exact_required_dictionary_shapes():
    event = ScreenEvent.model_validate({
        "id": "EVT-27",
        "type": "submit",
        "label": "Submit request",
        "trigger_component": "Request form",
        "business_rule_refs": ["BR-27"],
    })
    flow = NavigationFlow.model_validate({
        "from_event": "EVT-27",
        "to_screen_id": "SCREEN-028",
        "condition": "request_valid",
        "label": "Continue to review",
    })
    binding = DataBinding.model_validate({
        "field": "request_title",
        "entity": "ServiceRequest",
        "attribute": "title",
        "binding_type": "write",
    })
    interaction = ScreenInteraction.model_validate({
        "events": [event.model_dump()],
        "navigation_flows": [flow.model_dump()],
        "data_bindings": [binding.model_dump()],
        "validation_rules": [],
    })

    assert interaction.events[0].label == "Submit request"
    assert interaction.navigation_flows[0].to_screen_id == "SCREEN-028"
    assert interaction.data_bindings[0].entity == "ServiceRequest"


@pytest.mark.parametrize(
    ("model", "payload", "message"),
    [
        (ScreenEvent, {"type": "submit"}, "label"),
        (
            ScreenEvent,
            {"label": "Submit", "event_type": "submit"},
            "event_type",
        ),
        (NavigationFlow, {"from_event": "EVT-1"}, "to_screen_id"),
        (
            NavigationFlow,
            {"from_event": "EVT-1", "to_screen": "SCREEN-2"},
            "to_screen",
        ),
        (DataBinding, {"field": "claim_number"}, "entity"),
        (
            DataBinding,
            {"field": "claim_number", "entity": "Claim", "attribute_name": "number"},
            "attribute_name",
        ),
    ],
)
def test_interaction_models_reject_missing_required_or_misspelled_properties(model, payload, message):
    with pytest.raises(ValidationError) as exc:
        model.model_validate(payload)

    assert message in str(exc.value)


def test_interaction_collections_default_to_empty_and_accept_empty_arrays():
    assert ScreenInteraction.model_validate({}).model_dump() == {
        "events": [],
        "navigation_flows": [],
        "data_bindings": [],
        "validation_rules": [],
    }
    assert ScreenInteraction.model_validate({
        "events": [],
        "navigation_flows": [],
        "data_bindings": [],
        "validation_rules": [],
    }).events == []


def test_interaction_model_optional_properties_receive_defaults():
    event = ScreenEvent.model_validate({"label": "Open record"})
    flow = NavigationFlow.model_validate({
        "from_event": "EVT-27",
        "to_screen_id": "SCREEN-028",
    })
    binding = DataBinding.model_validate({
        "field": "record_id",
        "entity": "Record",
    })

    assert event.id == "EVT-001"
    assert event.business_rule_refs == []
    assert flow.condition == "always"
    assert flow.label is None
    assert binding.binding_type == "read_write"
    assert binding.attribute is None


@pytest.mark.parametrize(
    ("interaction", "path"),
    [
        ({"events": [{"type": "submit"}]}, "interaction.events.0.label"),
        (
            {"events": [{"label": 17}]},
            "interaction.events.0.label",
        ),
        (
            {"navigation_flows": [{"from_event": "EVT-1"}]},
            "interaction.navigation_flows.0.to_screen_id",
        ),
        (
            {"navigation_flows": [{"from_event": "EVT-1", "to_screen_id": ["SCREEN-2"]}]},
            "interaction.navigation_flows.0.to_screen_id",
        ),
        (
            {"data_bindings": [{"field": "claim_number"}]},
            "interaction.data_bindings.0.entity",
        ),
        (
            {"data_bindings": [{"field": "claim_number", "entity": 9}]},
            "interaction.data_bindings.0.entity",
        ),
        ({"events": "submit"}, "interaction.events"),
        ({"data_bindings": [None]}, "interaction.data_bindings.0"),
    ],
)
def test_screen_plan_rejects_malformed_interaction_objects_with_path_diagnostics(
    interaction,
    path,
    caplog,
):
    plan_data = _valid_plan_data()
    plan_data["screens"][0]["interaction"] = interaction

    with caplog.at_level("ERROR"):
        with pytest.raises(ScreenPlanValidationError) as exc:
            ScreenPlanService()._parse_and_validate_plan(plan_data)

    assert path in str(exc.value)
    assert path in caplog.text
    assert "expected_type=" in caplog.text
    assert "received=" in caplog.text


def test_gemini_interaction_validation_failure_retries_with_path_correction():
    service = ScreenPlanService()
    invalid_plan = _valid_plan_data()
    invalid_plan["screens"][0]["interaction"] = {
        "events": [{"id": "EVT-1", "type": "submit"}],
    }
    corrected_plan = _valid_plan_data()
    corrected_plan["screens"][0]["interaction"] = {
        "events": [{"id": "EVT-1", "type": "submit", "label": "Submit claim"}],
        "navigation_flows": [],
        "data_bindings": [],
        "validation_rules": [],
    }

    class FakeGemini:
        def __init__(self):
            self.prompts = []

        def generate_dict(self, prompt, response_schema=None, require_object=False):
            self.prompts.append(prompt)
            assert response_schema["type"] == "object"
            assert "$defs" not in response_schema
            return invalid_plan if len(self.prompts) == 1 else corrected_plan

    fake = FakeGemini()
    service.gemini = fake

    plan = service.generate_plan("Claims BRD: submit a claim.")

    assert len(fake.prompts) == 2
    assert "interaction.events.0.label" in fake.prompts[1]
    assert "expected string" in fake.prompts[1]
    assert plan.screens[0].interaction.events[0].label == "Submit claim"


def test_gemini_malformed_json_retries_once_with_corrective_instruction():
    service = ScreenPlanService()

    class FakeGemini:
        def __init__(self):
            self.prompts = []

        def generate_dict(self, prompt, response_schema=None, require_object=False):
            self.prompts.append(prompt)
            if len(self.prompts) == 1:
                raise RuntimeError("Invalid JSON from Gemini: incomplete object")
            return _valid_plan_data()

    fake = FakeGemini()
    service.gemini = fake

    plan = service.generate_plan("Claims BRD: review submitted claims.")

    assert len(fake.prompts) == 2
    assert "CORRECTIVE RETRY" in fake.prompts[1]
    assert plan.screens[0].name == "Claims Queue"


def test_empty_gemini_screens_retry_with_corrective_instruction():
    service = ScreenPlanService()

    class FakeGemini:
        def __init__(self):
            self.prompts = []

        def generate_dict(self, prompt, response_schema=None, require_object=False):
            self.prompts.append(prompt)
            return {**_valid_plan_data(), "screens": []} if len(self.prompts) == 1 else _valid_plan_data()

    fake = FakeGemini()
    service.gemini = fake

    plan = service.generate_plan("Requirements: staff must review submitted claims.")

    assert len(fake.prompts) == 2
    assert "contains no screens" in fake.prompts[1]
    assert plan.screens[0].name == "Claims Queue"


def test_interaction_schema_is_included_in_gemini_prompt():
    prompt = ScreenPlanService().build_planning_prompt("Healthcare BRD: record patient referrals.")

    assert "INTERACTION OBJECT JSON SCHEMA (authoritative" in prompt
    assert '"required": [' in prompt
    assert '"from_event"' in prompt
    assert '"to_screen_id"' in prompt
    assert '"field"' in prompt
    assert '"entity"' in prompt


def test_gemini_response_schema_is_fully_expanded_and_requires_interaction_fields():
    schema = ScreenPlanService._gemini_response_schema()
    screen_schema = schema["properties"]["screens"]["items"]
    interaction_schema = screen_schema["properties"]["interaction"]

    assert "$defs" not in schema
    assert "$ref" not in str(schema)
    assert schema["properties"]["screens"]["minItems"] == 1
    assert "screens" in schema["required"]
    assert "interaction" in screen_schema["required"]
    assert interaction_schema["required"] == [
        "events",
        "navigation_flows",
        "data_bindings",
        "validation_rules",
    ]
    assert interaction_schema["properties"]["events"]["items"]["required"] == ["label"]
    assert interaction_schema["properties"]["navigation_flows"]["items"]["required"] == [
        "from_event",
        "to_screen_id",
    ]
    assert interaction_schema["properties"]["data_bindings"]["items"]["required"] == [
        "field",
        "entity",
    ]


def test_numeric_component_field_values_are_normalized_to_display_strings():
    service = ScreenPlanService()
    plan_data = _valid_plan_data()
    plan_data["screens"][0]["components"][0]["fields"] = [
        {"label": "Claim number", "value": 12345},
        {"label": "Approved", "value": True},
        {"label": "Amount", "value": 75.5},
    ]

    plan = service._parse_and_validate_plan(plan_data)

    assert [field.value for field in plan.screens[0].components[0].fields] == [
        "12345",
        "True",
        "75.5",
    ]


@pytest.mark.parametrize(
    ("screen_update", "message"),
    [
        ({"purpose": ""}, "missing required property 'purpose'"),
        (
            {
                "components": [
                    {"type": "form", "fields": [{"type": "text"}]}
                ]
            },
            "label",
        ),
    ],
)
def test_invalid_screen_specification_is_rejected(screen_update, message):
    service = ScreenPlanService()
    plan_data = _valid_plan_data()
    plan_data["screens"][0].update(screen_update)

    with pytest.raises(ScreenPlanValidationError, match=message):
        service._parse_and_validate_plan(plan_data)


def test_complete_brd_is_sent_to_gemini_without_truncation(monkeypatch):
    service = ScreenPlanService()
    ending_requirement = "FINAL REQUIREMENT: preserve kitchen allergy warnings."
    source_text = "A" * 180025 + "\n" + ending_requirement

    class FakeGemini:
        def generate_dict(self, prompt, response_schema=None, require_object=False):
            assert "FULL BUSINESS REQUIREMENTS DOCUMENT (BRD)" in prompt
            assert ending_requirement in prompt
            assert "AVAILABLE BRD EXCERPT (TRUNCATED)" not in prompt
            assert response_schema["properties"]["screens"]["type"] == "array"
            return _valid_plan_data()

    service.gemini = FakeGemini()

    plan = service.generate_plan(source_text)

    assert plan.source_content_truncated is False
    assert plan.source_character_count == len(source_text)
    assert plan.analyzed_character_count == len(source_text)


def test_distinct_business_requirements_produce_dynamic_screen_plans():
    service = ScreenPlanService()

    class FakeGemini:
        def generate_dict(self, prompt, response_schema=None, require_object=False):
            if "Claims BRD" in prompt:
                return {
                    "application_name": "Claims Review",
                    "application_summary": "Adjudicate member claims.",
                    "screens": [
                        {
                            "sequence": 2,
                            "name": "Claim decision",
                            "purpose": "Approve or deny a medical claim.",
                            "screen_type": "approval",
                            "fields": [{"label": "Diagnosis code", "type": "text"}],
                        },
                        {
                            "sequence": 1,
                            "name": "Claims inbox",
                            "purpose": "Prioritize pending claims.",
                            "screen_type": "work_queue",
                            "tables": [{"columns": ["Claim number", "Member", "Evidence status"]}],
                        },
                    ],
                }
            return {
                "application_name": "Kitchen Operations",
                "application_summary": "Dispatch meal tickets.",
                "screens": [
                    {
                        "sequence": 1,
                        "name": "Kitchen ticket rail",
                        "purpose": "Prioritize preparation by pickup time.",
                        "screen_type": "work_queue",
                        "tables": [{"columns": ["Order", "Station", "Pickup time", "Allergy warning"]}],
                    }
                ],
            }

    service.gemini = FakeGemini()
    claims_plan = service.generate_plan("Claims BRD: review diagnosis evidence and member coverage.")
    kitchen_plan = service.generate_plan("Kitchen BRD: dispatch meal tickets and show allergy warnings.")

    assert [screen.name for screen in claims_plan.screens] == ["Claims inbox", "Claim decision"]
    assert len(claims_plan.screens) == 2
    assert claims_plan.screens[0].tables[0].columns == ["Claim number", "Member", "Evidence status"]
    assert claims_plan.screens[1].fields[0].label == "Diagnosis code"
    assert len(kitchen_plan.screens) == 1
    assert kitchen_plan.screens[0].tables[0].columns[-1] == "Allergy warning"
    assert kitchen_plan.screens[0].navigation_context["navigation_items"] == ["Kitchen ticket rail"]


@pytest.mark.parametrize(
    ("brd", "application_name", "screen_name", "interaction"),
    [
        (
            "Healthcare BRD: route patient referrals to clinical reviewers.",
            "Care Coordination",
            "Referral triage",
            {
                "events": [{"id": "REF-TRIAGE", "type": "select", "label": "Assign reviewer"}],
                "navigation_flows": [],
                "data_bindings": [
                    {"field": "patient_id", "entity": "Referral", "attribute": "patient_id", "binding_type": "read"}
                ],
                "validation_rules": [],
            },
        ),
        (
            "Inventory BRD: record stock adjustments and submit them for review.",
            "Inventory Control",
            "Stock adjustment",
            {
                "events": [{"id": "STOCK-SUBMIT", "type": "submit", "label": "Submit adjustment"}],
                "navigation_flows": [
                    {
                        "from_event": "STOCK-SUBMIT",
                        "to_screen_id": "SCREEN-002",
                        "condition": "adjustment_valid",
                    }
                ],
                "data_bindings": [
                    {"field": "quantity", "entity": "InventoryAdjustment", "attribute": "quantity", "binding_type": "write"}
                ],
                "validation_rules": ["Quantity must be provided."],
            },
        ),
    ],
)
def test_screen_interactions_validate_for_unrelated_brd_domains(
    brd,
    application_name,
    screen_name,
    interaction,
):
    service = ScreenPlanService()
    plan_data = {
        "application_name": application_name,
        "application_summary": f"Manage {application_name.lower()} workflows.",
        "screens": [{
            "screen_id": "SCREEN-001",
            "sequence": 1,
            "name": screen_name,
            "purpose": f"Complete the {screen_name.lower()} task.",
            "interaction": interaction,
        }],
    }

    class FakeGemini:
        def generate_dict(self, prompt, response_schema=None, require_object=False):
            assert brd in prompt
            assert response_schema["type"] == "object"
            assert require_object is True
            return plan_data

    service.gemini = FakeGemini()
    plan = service.generate_plan(brd)

    assert plan.screens[0].interaction is not None
    assert plan.screens[0].interaction.events[0].label


def test_screen_plan_rejects_duplicate_or_invalid_sequences():
    service = ScreenPlanService()
    plan_data = _valid_plan_data()
    plan_data["screens"].append(
        {
            **plan_data["screens"][0],
            "screen_id": "SCREEN-002",
            "name": "Second screen",
            "sequence": 1,
        }
    )

    with pytest.raises(ScreenPlanValidationError, match="duplicate sequence"):
        service._parse_and_validate_plan(plan_data)


def test_mock_screen_plan_endpoint_returns_422_for_invalid_plan(monkeypatch):
    def reject_plan(brd_text, project_name):
        raise ScreenPlanValidationError("Gemini screen plan contains no screens.")

    monkeypatch.setattr(
        "app.api.mock_screens.screen_plan_service.generate_plan",
        reject_plan,
    )

    response = client.post(
        "/api/ai/mock-screens/plan",
        json={"brd_text": "Requirements text", "project_name": "Claims"},
    )

    assert response.status_code == 422
    assert "Screen Plan Validation Failed" in response.json()["detail"]


def test_mock_screen_plan_endpoint_uses_pipeline_a_without_worker_authentication(monkeypatch):
    plan = ScreenPlanService()._parse_and_validate_plan(_valid_plan_data())
    monkeypatch.setattr(
        "app.api.mock_screens.screen_plan_service.generate_plan",
        lambda brd_text, project_name: plan,
    )

    response = client.post(
        "/api/ai/mock-screens/plan",
        json={"brd_text": "Complete BRD text", "project_name": "Claims"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_screens"] == 1
    assert payload["plan"]["screens"][0]["name"] == "Claims Queue"


def test_pipeline_a_render_endpoint_returns_png(monkeypatch):
    image_buffer = io.BytesIO()
    Image.new("RGB", (32, 24), color="white").save(image_buffer, format="PNG")
    png_bytes = image_buffer.getvalue()
    monkeypatch.setattr(
        "app.api.mock_screens.image_generation_service.generate_screen_image",
        lambda specification, design_context: png_bytes,
    )

    response = client.post(
        "/api/ai/mock-screens/render-screen",
        json={
            "specification": {
                "name": "Claims Queue",
                "purpose": "Review submitted claims",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mime_type"] == "image/png"
    assert payload["width"] == 32
    assert payload["height"] == 24
    assert base64.b64decode(payload["image_base64"]) == png_bytes


def test_pipeline_a_compile_pdf_endpoint_returns_pdf():
    image_buffer = io.BytesIO()
    Image.new("RGB", (32, 24), color="white").save(image_buffer, format="PNG")

    response = client.post(
        "/api/ai/mock-screens/compile-pdf",
        json={
            "application_name": "Claims Portal",
            "project_name": "Claims",
            "brd_name": "claims.pdf",
            "screens": [{
                "sequence": 1,
                "name": "Claims Queue",
                "image_base64": base64.b64encode(image_buffer.getvalue()).decode("ascii"),
            }],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    pdf_bytes = base64.b64decode(payload["pdf_base64"])
    assert pdf_bytes.startswith(b"%PDF")
    assert payload["page_count"] >= 2


def test_mock_screen_pdf_endpoint_returns_422_for_missing_images():
    response = client.post(
        "/api/ai/mock-screens/compile-pdf",
        json={
            "application_name": "Claims Portal",
            "screens": [{"sequence": 1, "name": "Claims queue"}],
        },
    )

    assert response.status_code == 422
    assert "Generated image missing" in response.json()["detail"]


def test_gemini_json_parser_reports_unrepairable_response(monkeypatch):
    service = GeminiService()
    monkeypatch.setattr(service, "generate_content", lambda prompt, **kwargs: "not valid json")

    with pytest.raises(RuntimeError, match="Invalid JSON from Gemini"):
        service.generate_dict("screen plan prompt")
