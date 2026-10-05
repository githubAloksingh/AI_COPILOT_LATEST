from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.api.schemas import (
    RequirementResult,
    RequirementItem,
    TestCaseItem,
    DefectResult,
    ReleaseNoteResult,
    DailyStatusResult,
    MockScreenComponent,
    MockScreenGenerationResponse,
    MockScreenSpecification,
    MockScreenPlanItem,
    MockScreensPlanResponse
)

client = TestClient(app)
settings.mock_screens_service_token = "test-mock-screens-service-token"
MOCK_SCREENS_HEADERS = {"X-Service-Token": settings.mock_screens_service_token}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-service"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"


@patch("app.services.retrieval_service.RetrievalService.store_chunks")
def test_ingest_endpoint(mock_store):
    mock_store.return_value = 2
    
    file_bytes = b"Requirement Document\nSystem shall support single sign on."
    files = {"file": ("test.txt", file_bytes, "text/plain")}
    data = {"document_id": "123", "file_name": "test.txt", "file_type": "text/plain"}
    
    response = client.post("/api/ai/ingest", data=data, files=files)
    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["status"] == "COMPLETED"
    assert resp_data["document_id"] == "123"
    assert resp_data["chunk_count"] == 2


@patch("app.services.gemini_service.GeminiService.generate_structured")
@patch("app.services.retrieval_service.RetrievalService.retrieve_relevant_context")
def test_requirement_generate_endpoint(mock_retrieval, mock_gemini):
    mock_retrieval.return_value = (["Relevant chunk 1"], [])
    mock_gemini.return_value = RequirementResult(
        requirements=[
            RequirementItem(
                requirementId="REQ-001",
                title="Auth Requirement",
                summary="User Authentication",
                userStory="As a user I want to log in",
                acceptanceCriteria=[],
                assumptions=[],
                dependencies=[],
                edgeCases=[]
            )
        ]
    )

    payload = {
        "title": "Auth Requirement",
        "description": "System shall provide user authentication.",
        "priority": "HIGH"
    }

    response = client.post("/api/ai/requirements/generate", json=payload)
    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["result"]["requirements"][0]["summary"] == "User Authentication"
    assert resp_data["model"] is not None


@patch("app.services.gemini_service.GeminiService.generate_structured_list")
@patch("app.services.retrieval_service.RetrievalService.retrieve_relevant_context")
def test_testcases_generate_endpoint(mock_retrieval, mock_gemini):
    mock_retrieval.return_value = ([], [])
    mock_gemini.return_value = [
        TestCaseItem(
            scenario="Login with valid password",
            type="POSITIVE",
            priority="HIGH",
            preconditions=["User exists"],
            steps=["Enter email", "Enter password", "Submit"],
            expectedResult="User logs in"
        )
    ]

    payload = {
        "requirement": "User Login",
        "acceptanceCriteria": "Must enter valid pass",
        "testTypes": ["POSITIVE"]
    }

    response = client.post("/api/ai/test-cases/generate", json=payload)
    assert response.status_code == 200
    resp_data = response.json()
    assert len(resp_data["result"]) == 1
    assert resp_data["result"][0]["scenario"] == "Login with valid password"


def test_testcases_direct_upload_endpoint_is_removed():
    response = client.post("/api/ai/test-cases/generate-upload")
    assert response.status_code == 404


@patch("app.api.routes.rag_service.plan_mock_screens")
def test_mock_screens_plan_endpoint_returns_ordered_plan_only(mock_plan):
    mock_plan.return_value = MockScreensPlanResponse(
        screens=[
            MockScreenPlanItem(
                sequence=1,
                screenName="Enrollment",
                purpose="Start enrollment",
                relevantRequirements=["Collect required customer details"]
            )
        ],
        model="gemini-test",
        prompt_version="mock-screens-plan-v1",
        execution_time_ms=12
    )

    response = client.post(
        "/api/ai/mock-screens/plan",
        json={"document_id": "42", "prompt": "Plan customer enrollment screens"},
        headers=MOCK_SCREENS_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["screens"][0]["sequence"] == 1
    assert payload["screens"][0]["screenName"] == "Enrollment"
    assert "html" not in payload
    mock_plan.assert_called_once()


@patch("app.api.routes.rag_service.plan_mock_screens", side_effect=ValueError("No indexed BRD content"))
def test_mock_screens_plan_endpoint_rejects_missing_document_content(mock_plan):
    response = client.post(
        "/api/ai/mock-screens/plan",
        json={"document_id": "42", "prompt": "Plan customer enrollment screens"},
        headers=MOCK_SCREENS_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "No indexed BRD content"
    mock_plan.assert_called_once()


@patch("app.api.routes.rag_service.generate_mock_screen")
def test_mock_screens_generation_endpoint_returns_one_screen_specification(mock_generate):
    mock_generate.return_value = MockScreenGenerationResponse(
        screen=MockScreenSpecification(
            sequence=2,
            screenName="Review",
            purpose="Review enrollment details",
            layoutDescription="A review panel with a confirmation action.",
            components=[MockScreenComponent(componentType="button", label="Confirm")]
        ),
        model="gemini-test",
        prompt_version="mock-screen-spec-v1",
        execution_time_ms=15
    )

    response = client.post("/api/ai/mock-screens/generate-screen", json={
        "document_id": "42",
        "prompt": "Create an enrollment flow",
        "sequence": 2,
        "screen_name": "Review",
        "purpose": "Review enrollment details",
        "relevant_requirements": ["Review before confirmation"],
        "previous_screens": []
    }, headers=MOCK_SCREENS_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["screen"]["sequence"] == 2
    assert payload["screen"]["screenName"] == "Review"
    assert "screens" not in payload
    mock_generate.assert_called_once()


def test_mock_screens_plan_endpoint_rejects_unauthenticated_requests():
    with patch("app.api.routes.rag_service.plan_mock_screens") as mock_plan:
        response = client.post(
            "/api/ai/mock-screens/plan",
            json={"document_id": "42", "prompt": "Plan customer enrollment screens"},
        )

    assert response.status_code == 401
    mock_plan.assert_not_called()


def test_mock_screens_generation_endpoint_rejects_unauthenticated_requests():
    with patch("app.api.routes.rag_service.generate_mock_screen") as mock_generate:
        response = client.post("/api/ai/mock-screens/generate-screen", json={
            "document_id": "42",
            "prompt": "Create an enrollment flow",
            "sequence": 1,
            "screen_name": "Enrollment",
            "purpose": "Start enrollment",
            "relevant_requirements": ["Enter customer data"],
            "previous_screens": []
        })

    assert response.status_code == 401
    mock_generate.assert_not_called()


def test_mock_screens_plan_endpoint_rejects_invalid_service_token():
    response = client.post(
        "/api/ai/mock-screens/plan",
        json={"document_id": "42", "prompt": "Plan customer enrollment screens"},
        headers={"X-Service-Token": "invalid"},
    )

    assert response.status_code == 401


def test_cors_allows_local_frontend_and_rejects_unconfigured_origin():
    allowed = client.options(
        "/api/ai/mock-screens/plan",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "POST",
        },
    )
    rejected = client.options(
        "/api/ai/mock-screens/plan",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:4200"
    assert "access-control-allow-origin" not in rejected.headers

