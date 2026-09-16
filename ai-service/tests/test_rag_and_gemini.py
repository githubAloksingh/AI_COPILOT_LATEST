from app.services.gemini_service import GeminiService
from app.services.rag_service import RagService
from app.prompts import (
    build_requirement_prompt,
    build_testcase_prompt,
    build_defect_prompt,
    build_release_notes_prompt,
    build_daily_status_prompt,
    GUARDRAILS
)
from app.api.schemas import RequirementGenerateRequest, RequirementResult, DefectResult


def test_clean_json_markdown():
    raw = "```json\n{\"summary\": \"Test summary\", \"userStory\": \"Story\"}\n```"
    cleaned = GeminiService.clean_json(raw)
    assert cleaned == "{\"summary\": \"Test summary\", \"userStory\": \"Story\"}"


def test_clean_json_with_prose():
    raw = "Here is the response:\n{\"summary\": \"Test summary\"}\nHope this helps!"
    cleaned = GeminiService.clean_json(raw)
    assert cleaned == "{\"summary\": \"Test summary\"}"


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


def test_technical_design_uses_full_selected_brd_context(monkeypatch):
    class FakeRetrieval:
        def retrieve_document_context(self, document_id):
            assert document_id == "42"
            return [
                "Section 1: System must allow user login with email and password.",
                "Section 2: Admin can review failed login attempts and lock accounts after 5 attempts."
            ], [
                {"document_id": "42", "file_name": "selected_brd.pdf", "chunk_index": 0, "snippet": "Section 1"},
                {"document_id": "42", "file_name": "selected_brd.pdf", "chunk_index": 1, "snippet": "Section 2"}
            ]

        def retrieve_relevant_context(self, query, top_k=None, document_id=None):
            raise AssertionError("Technical Design generation must use the full selected BRD document context, not a filtered relevance search.")

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
