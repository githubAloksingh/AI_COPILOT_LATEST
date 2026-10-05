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
from app.api.schemas import (
    DefectResult,
    MockScreensContextSummary,
    MockScreensPlan,
    MockScreensPlanRequest,
    MockScreenPlanItem,
    MockScreenComponent,
    MockScreenGenerationRequest,
    MockScreenSpecification,
    RequirementGenerateRequest,
    RequirementResult,
)


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


def test_mock_screen_planning_analyzes_every_brd_chunk_and_requested_scope():
    source_chunks = ["CHUNK_ONE " + ("A" * 12000), "CHUNK_TWO " + ("B" * 12000)]

    class FakeRetrieval:
        def retrieve_document_context(self, document_id):
            assert document_id == "42"
            return source_chunks, []

    class FakeGemini:
        summary_count = 0

        def generate_structured(self, prompt, schema):
            if schema is MockScreensContextSummary:
                self.summary_count += 1
                marker = "CHUNK_ONE" if self.summary_count == 1 else "CHUNK_TWO"
                assert marker in prompt
                return MockScreensContextSummary(
                    requirements=[f"Requirement from {marker}"],
                    workflows=[],
                    constraints=[]
                )

            assert schema is MockScreensPlan
            assert "Focus only on the customer enrollment flow" in prompt
            assert "Requirement from CHUNK_ONE" in prompt
            assert "Requirement from CHUNK_TWO" in prompt
            return MockScreensPlan(screens=[
                MockScreenPlanItem(
                    sequence=1,
                    screenName="Enrollment",
                    purpose="Start customer enrollment",
                    relevantRequirements=["Requirement from CHUNK_ONE"]
                ),
                MockScreenPlanItem(
                    sequence=2,
                    screenName="Review",
                    purpose="Review enrollment details",
                    relevantRequirements=["Requirement from CHUNK_TWO"]
                )
            ])

    service = RagService()
    service.retrieval = FakeRetrieval()
    service.gemini = FakeGemini()

    response = service.plan_mock_screens(MockScreensPlanRequest(
        document_id="42",
        prompt="Focus only on the customer enrollment flow"
    ))

    assert [screen.sequence for screen in response.screens] == [1, 2]
    assert response.screens[0].screenName == "Enrollment"
    assert service.gemini.summary_count == 2


def test_mock_screen_plan_rejects_noncontiguous_sequence_numbers():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="contiguous starting at 1"):
        MockScreensPlan(screens=[
            MockScreenPlanItem(
                sequence=1,
                screenName="Start",
                purpose="Begin",
                relevantRequirements=["Requirement one"]
            ),
            MockScreenPlanItem(
                sequence=3,
                screenName="Finish",
                purpose="Complete",
                relevantRequirements=["Requirement two"]
            )
        ])


def test_mock_screen_generation_uses_selected_brd_and_preserves_planned_sequence():
    class FakeRetrieval:
        def retrieve_relevant_context(self, query, top_k=None, document_id=None):
            assert document_id == "42"
            assert top_k >= 10
            assert "Review enrollment details" in query
            return ["The BRD requires a confirmation before account creation."], []

    class FakeGemini:
        def generate_structured(self, prompt, schema):
            assert schema is MockScreenSpecification
            assert "The BRD requires a confirmation before account creation." in prompt
            assert "Enrollment" in prompt
            assert "Review enrollment details" in prompt
            assert "Collect customer details" in prompt
            return MockScreenSpecification(
                sequence=2,
                screenName="Review",
                purpose="Review enrollment details",
                layoutDescription="A review panel followed by a confirmation action.",
                components=[
                    MockScreenComponent(componentType="header", label="Review details"),
                    MockScreenComponent(componentType="button", label="Confirm")
                ],
                interactionNotes=["Confirm proceeds to account creation."]
            )

    service = RagService()
    service.retrieval = FakeRetrieval()
    service.gemini = FakeGemini()

    response = service.generate_mock_screen(MockScreenGenerationRequest(
        document_id="42",
        prompt="Create the enrollment flow",
        sequence=2,
        screen_name="Review",
        purpose="Review enrollment details",
        relevant_requirements=["Review before account creation"],
        previous_screens=[MockScreenSpecification(
            sequence=1,
            screenName="Enrollment",
            purpose="Start enrollment",
            layoutDescription="Collect customer details.",
            components=[MockScreenComponent(componentType="input", label="Name")]
        )]
    ))

    assert response.screen.sequence == 2
    assert response.screen.screenName == "Review"


def test_mock_screen_generation_rejects_output_for_different_planned_screen():
    class FakeRetrieval:
        def retrieve_relevant_context(self, query, top_k=None, document_id=None):
            return ["BRD context"], []

    class FakeGemini:
        def generate_structured(self, prompt, schema):
            return MockScreenSpecification(
                sequence=3,
                screenName="Wrong screen",
                purpose="Not the planned screen",
                layoutDescription="Invalid mismatch.",
                components=[MockScreenComponent(componentType="text", label="Wrong")]
            )

    service = RagService()
    service.retrieval = FakeRetrieval()
    service.gemini = FakeGemini()

    import pytest
    with pytest.raises(ValueError, match="does not match its planned sequence and name"):
        service.generate_mock_screen(MockScreenGenerationRequest(
            document_id="42",
            prompt="Create screens",
            sequence=2,
            screen_name="Review",
            purpose="Review details",
            relevant_requirements=["Review before confirmation"]
        ))


def test_mock_screen_specification_normalizes_common_gemini_field_aliases():
    screen = MockScreenSpecification.model_validate({
        "screenNumber": 1,
        "screenName": "Login",
        "screenPurpose": "Authenticate the customer",
        "layout": "centered login card",
        "components": [{"componentType": "input", "label": "Customer ID"}],
        "interactionNotes": "Forgot Password opens account recovery."
    })

    assert screen.sequence == 1
    assert screen.purpose == "Authenticate the customer"
    assert screen.layoutDescription == "centered login card"
    assert screen.interactionNotes == ["Forgot Password opens account recovery."]
