from app.services.gemini_service import GeminiService
from app.services.rag_service import RagService
from app.prompts import (
    build_requirement_prompt,
    build_testcase_prompt,
    build_defect_prompt,
    build_release_notes_prompt,
    GUARDRAILS
)
from app.api.schemas import RequirementGenerateRequest, RequirementResult


def test_clean_json_markdown():
    raw = "```json\n{\"summary\": \"Test summary\", \"userStory\": \"Story\"}\n```"
    cleaned = GeminiService.clean_json(raw)
    assert cleaned == "{\"summary\": \"Test summary\", \"userStory\": \"Story\"}"


def test_clean_json_with_prose():
    raw = "Here is the response:\n{\"summary\": \"Test summary\"}\nHope this helps!"
    cleaned = GeminiService.clean_json(raw)
    assert cleaned == "{\"summary\": \"Test summary\"}"


def test_gemini_api_key_is_sent_in_header_not_url(monkeypatch):
    from app.services import gemini_service as gemini_service_module

    captured_request = {}

    class Response:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {"content": {"parts": [{"text": "generated"}]}}
                ]
            }

    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def post(self, url, json, headers):
            captured_request.update(url=url, body=json, headers=headers)
            return Response()

    monkeypatch.setattr(gemini_service_module.httpx, "Client", Client)
    monkeypatch.setattr(gemini_service_module.settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(gemini_service_module.settings, "gemini_model", "test-model")
    service = GeminiService()
    service.candidate_models = []

    assert service.generate_content("prompt") == "generated"
    assert "test-api-key" not in captured_request["url"]
    assert captured_request["headers"]["x-goog-api-key"] == "test-api-key"


def test_gemini_request_uses_supplied_response_json_schema(monkeypatch):
    from app.services import gemini_service as gemini_service_module

    captured_request = {}

    class Response:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}

    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def post(self, url, json, headers):
            captured_request["body"] = json
            return Response()

    monkeypatch.setattr(gemini_service_module.httpx, "Client", Client)
    monkeypatch.setattr(gemini_service_module.settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(gemini_service_module.settings, "gemini_model", "test-model")
    service = GeminiService()
    service.candidate_models = []
    schema = {"type": "object", "properties": {"label": {"type": "string"}}}

    assert service.generate_content("prompt", response_schema=schema) == "{}"
    assert captured_request["body"]["contents"] == [
        {"parts": [{"text": "prompt"}]}
    ]
    generation_config = captured_request["body"]["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert generation_config["maxOutputTokens"] == 65536
    assert generation_config["responseJsonSchema"] == schema
    assert "temperature" not in generation_config


def test_gemini_request_preserves_mock_screen_structured_schema(monkeypatch):
    from app.services import gemini_service as gemini_service_module
    from app.services.screen_plan_service import ScreenPlanService

    captured_request = {}

    class Response:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}

    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def post(self, url, json, headers):
            captured_request.update(url=url, body=json, headers=headers)
            return Response()

    monkeypatch.setattr(gemini_service_module.httpx, "Client", Client)
    monkeypatch.setattr(gemini_service_module.settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(gemini_service_module.settings, "gemini_model", "test-model")
    service = GeminiService()
    service.candidate_models = []
    schema = ScreenPlanService._gemini_response_schema()
    prompt = "Screen planning prompt with BRD"

    assert service.generate_content(prompt, response_schema=schema) == "{}"
    assert captured_request["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/test-model:generateContent"
    )
    assert captured_request["body"]["contents"] == [{"parts": [{"text": prompt}]}]
    generation_config = captured_request["body"]["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert generation_config["responseJsonSchema"] == schema
    assert len(str(schema)) > 10000


def test_gemini_fallback_reports_model_that_generated_response(monkeypatch):
    from app.services import gemini_service as gemini_service_module

    requested_urls = []

    class Response:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = "provider response must not be logged"

        def json(self):
            return self._payload

    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def post(self, url, json, headers):
            requested_urls.append(url)
            if len(requested_urls) == 1:
                return Response(404, {"error": {"status": "NOT_FOUND"}})
            return Response(
                200,
                {"candidates": [{"content": {"parts": [{"text": "generated"}]}}]},
            )

    monkeypatch.setattr(gemini_service_module.httpx, "Client", Client)
    monkeypatch.setattr(gemini_service_module.settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(gemini_service_module.settings, "gemini_model", "gemini-3.5-flash-lite")
    service = GeminiService()
    service.candidate_models = ["gemini-2.5-flash"]

    assert service.generate_content("private BRD prompt") == "generated"
    assert requested_urls == [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    ]
    assert service.last_used_model == "gemini-2.5-flash"


def test_gemini_failure_diagnostics_preserve_model_errors_without_sensitive_content(
    monkeypatch, caplog
):
    from app.services import gemini_service as gemini_service_module

    class Response:
        status_code = 404
        text = "private BRD text and test-api-key"

        def json(self):
            return {"error": {"status": "NOT_FOUND", "message": self.text}}

    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def post(self, url, json, headers):
            return Response()

    monkeypatch.setattr(gemini_service_module.httpx, "Client", Client)
    monkeypatch.setattr(gemini_service_module.settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(gemini_service_module.settings, "gemini_model", "gemini-3.5-flash-lite")
    service = GeminiService()
    service.candidate_models = ["gemini-2.5-flash"]

    import logging
    with caplog.at_level(logging.WARNING, logger="app.services.gemini_service"):
        try:
            service.generate_content("private BRD text")
        except RuntimeError as error:
            diagnostics = str(error)
        else:
            raise AssertionError("Expected Gemini model attempts to fail")

    assert '"model":"gemini-3.5-flash-lite","http_status":404,"status":"NOT_FOUND"' in diagnostics
    assert '"model":"gemini-2.5-flash","http_status":404,"status":"NOT_FOUND"' in diagnostics
    assert '"model":"gemini-3.5-flash-lite","http_status":404' in caplog.text
    assert '"model":"gemini-2.5-flash","http_status":404' in caplog.text
    assert "private BRD text" not in diagnostics
    assert "private BRD text" not in caplog.text
    assert "[redacted]" in diagnostics
    assert "test-api-key" not in diagnostics
    assert "test-api-key" not in caplog.text


def test_gemini_invalid_argument_diagnostic_keeps_safe_google_details(monkeypatch, caplog):
    import logging
    from app.services import gemini_service as gemini_service_module

    class Response:
        status_code = 400
        text = "must not be logged"

        def json(self):
            return {
                "error": {
                    "code": 400,
                    "status": "INVALID_ARGUMENT",
                    "message": "Unsupported schema keyword for private BRD text; api_key=test-api-key",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.BadRequest",
                            "fieldViolations": [
                                {
                                    "field": "generationConfig.responseJsonSchema",
                                    "description": "Unsupported anyOf; private BRD text; test-api-key",
                                }
                            ],
                            "ignoredSensitiveField": "do not include",
                        }
                    ],
                }
            }

    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def post(self, url, json, headers):
            return Response()

    monkeypatch.setattr(gemini_service_module.httpx, "Client", Client)
    monkeypatch.setattr(gemini_service_module.settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(gemini_service_module.settings, "gemini_model", "test-model")
    service = GeminiService()
    service.candidate_models = []

    with caplog.at_level(logging.WARNING, logger="app.services.gemini_service"):
        try:
            service.generate_content("private BRD text")
        except RuntimeError as error:
            diagnostic = str(error)
        else:
            raise AssertionError("Expected the mocked invalid request to fail")

    assert '"http_status":400' in diagnostic
    assert '"provider_code":400' in diagnostic
    assert '"status":"INVALID_ARGUMENT"' in diagnostic
    assert "Unsupported schema keyword" in diagnostic
    assert "generationConfig.responseJsonSchema" in diagnostic
    assert "fieldViolations" in diagnostic
    assert "private BRD text" not in diagnostic
    assert "test-api-key" not in diagnostic
    assert "ignoredSensitiveField" not in diagnostic
    assert "private BRD text" not in caplog.text
    assert "test-api-key" not in caplog.text


def test_gemini_model_configuration_uses_only_confirmed_candidates():
    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert settings.gemini_candidate_models == [
        "gemini-3.7-flash",
        "gemini-3.8-flash",
    ]


def test_prompt_builders_include_guardrails():
    req_prompt = build_requirement_prompt("User login", "User context")
    assert GUARDRAILS in req_prompt
    assert "User login" in req_prompt
    assert "User context" in req_prompt

    tc_prompt = build_testcase_prompt("User login", "Must enter valid pass", ["POSITIVE"], "Context")
    assert GUARDRAILS in tc_prompt
    assert "POSITIVE" in tc_prompt

    defect_prompt = build_defect_prompt("500 Error", "NullPointer", "stack trace", "step 1", "crash", "success", "Context")
    assert GUARDRAILS in defect_prompt
    assert "500 Error" in defect_prompt


def test_technical_design_uses_500_relevant_selected_brd_chunks(monkeypatch):
    class FakeRetrieval:
        def retrieve_relevant_context(self, query, top_k=None, document_id=None):
            assert document_id == "42"
            assert top_k == 500
            return [
                "Section 1: System must allow user login with email and password.",
                "Section 2: Admin can review failed login attempts and lock accounts after 5 attempts."
            ], [
                {"document_id": "42", "file_name": "selected_brd.pdf", "chunk_index": 0, "snippet": "Section 1"},
                {"document_id": "42", "file_name": "selected_brd.pdf", "chunk_index": 1, "snippet": "Section 2"}
            ]

    class FakeGemini:
        def generate_dict(self, prompt):
            assert "System must allow user login with email and password" in prompt
            assert "Admin can review failed login attempts and lock accounts after 5 attempts" in prompt
            return {
                "technicalDesign": {
                    "title": "Login and Lockout Technical Design",
                    "objective": "Implement the BRD-supported login flow.",
                    "requirementSummary": "Summary derived from the selected BRD.",
                    "technicalOverview": {
                        "whatIsBeingImplemented": "User login and account lockout workflow.",
                        "technicalObjective": "Implement the selected BRD requirements.",
                        "scopeOfImplementation": ["Login workflow", "Failed attempt tracking"],
                        "outOfScope": [],
                        "highLevelApproach": "Follow the selected BRD process.",
                        "relationshipToUserStory": "Not specified in BRD"
                    },
                    "keyArchitecturalPrinciples": [],
                    "systemOverview": {
                        "highLevelArchitecture": "Not specified in BRD",
                        "flowchartSteps": []
                    },
                    "architectureOverview": {
                        "frontendComponents": [],
                        "backendServices": [],
                        "apis": [],
                        "databaseStorage": "Not specified in BRD",
                        "externalSystems": [],
                        "communicationFlow": "Not specified in BRD",
                        "textFlowDiagram": "Not specified in BRD"
                    },
                    "components": [],
                    "componentDesign": [],
                    "frontendDesign": {
                        "angularComponents": [], "services": [], "models": [],
                        "formsAndState": "Not specified in BRD", "apiIntegration": "Not specified in BRD",
                        "editModeBehavior": "Not specified in BRD", "validation": [],
                        "loadingAndErrorStates": "Not specified in BRD", "uiStateTransitions": "Not specified in BRD"
                    },
                    "backendDesign": {
                        "endpoints": [], "controllers": [], "businessServices": [], "repositoryLayer": [],
                        "validation": [], "errorHandling": [], "security": []
                    },
                    "apis": [],
                    "dataModel": [],
                    "dataFlow": [],
                    "processFlows": [],
                    "integrations": [],
                    "validation": [],
                    "validationRules": {},
                    "businessLogic": [],
                    "businessRuleMappings": [],
                    "acceptanceCriteriaMappings": [],
                    "errorHandling": [],
                    "edgeCases": [],
                    "security": [],
                    "databaseChanges": [],
                    "dependencies": [],
                    "assumptions": [],
                    "implementationNotes": [],
                    "implementationPlan": [],
                    "testingStrategy": [],
                    "technicalRisks": [],
                    "openQuestions": []
                }
            }

    service = RagService()
    service.retrieval = FakeRetrieval()
    service.gemini = FakeGemini()

    resp = service.generate_technical_design(RequirementGenerateRequest(
        title="Selected BRD technical design",
        description="Generate technical design from the selected BRD.",
        document_id="42"
    ))

    assert resp.result.technicalDesign["title"] == "Login and Lockout Technical Design"
    assert resp.sources == ["Section 1", "Section 2"]
