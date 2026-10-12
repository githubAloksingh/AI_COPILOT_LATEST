import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_document_content
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
        lambda prompt: (_ for _ in ()).throw(
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
        def generate_dict(self, prompt):
            assert "FULL BUSINESS REQUIREMENTS DOCUMENT (BRD)" in prompt
            assert ending_requirement in prompt
            assert "AVAILABLE BRD EXCERPT (TRUNCATED)" not in prompt
            return _valid_plan_data()

    service.gemini = FakeGemini()

    plan = service.generate_plan(source_text)

    assert plan.source_content_truncated is False
    assert plan.source_character_count == len(source_text)
    assert plan.analyzed_character_count == len(source_text)


def test_distinct_business_requirements_produce_dynamic_screen_plans():
    service = ScreenPlanService()

    class FakeGemini:
        def generate_dict(self, prompt):
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
    monkeypatch.setattr(service, "generate_content", lambda prompt: "not valid json")

    with pytest.raises(RuntimeError, match="Invalid JSON from Gemini"):
        service.generate_dict("screen plan prompt")
