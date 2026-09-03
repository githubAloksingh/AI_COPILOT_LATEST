from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.schemas import (
    RequirementResult,
    RequirementItem,
    TestCaseItem,
    DefectResult,
    ReleaseNoteResult,
    DailyStatusResult
)

client = TestClient(app)


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


@patch("app.services.gemini_service.GeminiService.generate_structured_list")
def test_testcases_generate_upload_endpoint(mock_gemini):
    import io
    import zipfile

    mock_gemini.return_value = [
        TestCaseItem(
            scenario="Verify BRD Requirement R1 against UserController",
            type="POSITIVE",
            priority="HIGH",
            preconditions=["Server running"],
            steps=["POST /login", "Verify 200 OK"],
            expectedResult="User authenticated successfully"
        )
    ]

    # Create dummy zip in memory
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr("src/UserController.java", "public class UserController { public String login() { return \"ok\"; } }")
    zip_bytes = zip_buf.getvalue()

    brd_bytes = b"BRD Specification: The system must allow users to log in."

    files = {
        "brd_file": ("spec.txt", brd_bytes, "text/plain"),
        "zip_file": ("project.zip", zip_bytes, "application/zip")
    }
    data = {
        "input_mode": "both",
        "test_types": "Functional Tests,Edge & Boundary Cases"
    }

    response = client.post("/api/ai/test-cases/generate-upload", data=data, files=files)
    assert response.status_code == 200
    resp_data = response.json()
    assert len(resp_data["result"]) == 1
    assert resp_data["result"][0]["scenario"] == "Verify BRD Requirement R1 against UserController"
    assert any("BRD" in s for s in resp_data["sources"])
    assert any("ZIP" in s for s in resp_data["sources"])

