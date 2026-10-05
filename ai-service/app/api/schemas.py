from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ----------------------------------------------------
# Common & Source Models
# ----------------------------------------------------
class SourceDto(BaseModel):
    document_id: Optional[str] = None
    file_name: Optional[str] = None
    chunk_index: Optional[int] = None
    snippet: Optional[str] = None


# ----------------------------------------------------
# Ingestion Models
# ----------------------------------------------------
class IngestionResponse(BaseModel):
    status: str
    document_id: str
    file_name: str
    chunk_count: int
    chunks: Optional[List[str]] = None
    message: str


# ----------------------------------------------------
# Retrieval Models
# ----------------------------------------------------
class RetrieveRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    document_id: Optional[str] = None


class RetrieveResponse(BaseModel):
    query: str
    chunks: List[str]
    sources: List[SourceDto]


# ----------------------------------------------------
# Mock Screens Planning Models
# ----------------------------------------------------
class MockScreensPlanRequest(BaseModel):
    document_id: str

    @field_validator("document_id")
    @classmethod
    def validate_required_text(cls, value):
        if not value or not value.strip():
            raise ValueError("Field must not be empty")
        return value.strip()


class MockScreensContextSummary(BaseModel):
    requirements: List[str] = Field(default_factory=list)
    workflows: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class MockScreenPlanItem(BaseModel):
    sequence: int = Field(gt=0)
    screenName: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    relevantRequirements: List[str] = Field(min_length=1)


class MockScreensPlan(BaseModel):
    screens: List[MockScreenPlanItem] = Field(min_length=1)

    @field_validator("screens")
    @classmethod
    def validate_screen_sequence(cls, screens):
        expected = list(range(1, len(screens) + 1))
        actual = [screen.sequence for screen in screens]
        if actual != expected:
            raise ValueError("Screen sequences must be ordered and contiguous starting at 1")
        return screens


class MockScreensPlanResponse(BaseModel):
    screens: List[MockScreenPlanItem]
    model: str
    prompt_version: str
    execution_time_ms: int


class MockScreenComponent(BaseModel):
    componentType: Literal[
        "header", "navigation", "text", "button", "input", "select",
        "checkbox", "radio", "table", "card", "modal", "alert", "imagePlaceholder"
    ]
    label: str = ""
    description: Optional[str] = ""
    required: bool = False
    options: List[str] = Field(default_factory=list)


class MockScreenSpecification(BaseModel):
    sequence: int = Field(gt=0)
    screenName: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    layoutDescription: str = Field(min_length=1)
    components: List[MockScreenComponent] = Field(min_length=1)
    interactionNotes: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_generated_screen(cls, value):
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        aliases = {
            "sequence": ("screenSequence", "screenNumber", "screen_sequence", "screen_number"),
            "screenName": ("screen_name", "title"),
            "purpose": ("screenPurpose", "screen_purpose"),
            "layoutDescription": ("layout", "layout_description", "layoutType", "layout_type"),
            "interactionNotes": ("interaction_notes", "interactions", "userFlow", "user_flow"),
        }
        for field_name, field_aliases in aliases.items():
            if field_name not in normalized:
                for alias in field_aliases:
                    if alias in normalized:
                        normalized[field_name] = normalized[alias]
                        break

        notes = normalized.get("interactionNotes")
        if isinstance(notes, str):
            normalized["interactionNotes"] = [notes] if notes.strip() else []
        elif notes is not None and not isinstance(notes, list):
            normalized["interactionNotes"] = [str(notes)]
        return normalized


class MockScreenGenerationRequest(BaseModel):
    document_id: str
    sequence: int = Field(gt=0)
    screen_name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    relevant_requirements: List[str] = Field(min_length=1)
    previous_screens: List[MockScreenSpecification] = Field(default_factory=list)

    @field_validator("document_id", "screen_name", "purpose")
    @classmethod
    def validate_required_text(cls, value):
        if not value or not value.strip():
            raise ValueError("Field must not be empty")
        return value.strip()


class MockScreenGenerationResponse(BaseModel):
    screen: MockScreenSpecification
    model: str
    prompt_version: str
    execution_time_ms: int


# ----------------------------------------------------
# Requirements Models
# ----------------------------------------------------
class RequirementGenerateRequest(BaseModel):
    title: str
    description: str
    document_id: Optional[str] = None


class GroundedItem(BaseModel):
    text: str
    grounding: str = "EXPLICIT"  # EXPLICIT, DERIVED, REQUIRES_CONFIRMATION
    source: Optional[List[str]] = Field(default_factory=list)

    @classmethod
    def from_any(cls, val):
        if isinstance(val, cls):
            return val
        if isinstance(val, dict):
            src = val.get("source", [])
            if not isinstance(src, list):
                src = [str(src)] if src else []
            return cls(
                text=str(val.get("text", "")),
                grounding=str(val.get("grounding", "EXPLICIT")),
                source=[str(s) for s in src if s]
            )
        if isinstance(val, str):
            return cls(text=val, grounding="EXPLICIT", source=[])
        return cls(text=str(val), grounding="EXPLICIT", source=[])


class RequirementItem(BaseModel):
    requirementId: str = "REQ-001"
    userStoryId: Optional[str] = None
    title: str = ""
    summary: str = ""
    userStory: str = ""
    description: Optional[str] = ""
    acceptanceCriteria: List[GroundedItem] = Field(default_factory=list)
    businessRules: List[GroundedItem] = Field(default_factory=list)
    assumptions: List[GroundedItem] = Field(default_factory=list)
    dependencies: List[GroundedItem] = Field(default_factory=list)
    edgeCases: List[GroundedItem] = Field(default_factory=list)
    sources: Optional[List[str]] = Field(default_factory=list)

    @field_validator("acceptanceCriteria", "businessRules", "assumptions", "dependencies", "edgeCases", mode="before")
    @classmethod
    def coerce_grounded_items(cls, v):
        if not isinstance(v, list):
            return []
        return [GroundedItem.from_any(item) for item in v]


class RequirementResult(BaseModel):
    requirements: List[RequirementItem] = Field(default_factory=list)
    userStories: Optional[List[dict]] = Field(default_factory=list)
    functionalDesign: Optional[dict] = None
    technicalDesign: Optional[dict] = None


class RequirementGenerateResponse(BaseModel):
    result: RequirementResult
    sources: List[str] = Field(default_factory=list)
    source_details: List[SourceDto] = Field(default_factory=list)
    model: str
    prompt_version: str
    execution_time_ms: int


# ----------------------------------------------------
# Test Cases Models
# ----------------------------------------------------
class TestCaseGenerateRequest(BaseModel):
    requirement: str
    acceptanceCriteria: Optional[str] = ""
    testTypes: List[str] = Field(default_factory=lambda: ["POSITIVE", "NEGATIVE", "EDGE"])
    document_id: Optional[str] = None
    zip_document_id: Optional[str] = None


class TestCaseItem(BaseModel):
    __test__ = False
    tcId: Optional[str] = None
    requirementId: Optional[str] = None
    scenario: str
    preconditions: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    expectedResult: str = ""


class TestCaseGenerateResponse(BaseModel):
    result: List[TestCaseItem]
    sources: List[str] = Field(default_factory=list)
    source_details: List[SourceDto] = Field(default_factory=list)
    model: str
    prompt_version: str
    execution_time_ms: int


# ----------------------------------------------------
# Defect Models
# ----------------------------------------------------
class DefectAnalyzeRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    logs: Optional[str] = ""
    stepsToReproduce: Optional[str] = ""
    actualBehavior: Optional[str] = ""
    expectedBehavior: Optional[str] = ""
    environment: Optional[str] = ""
    document_id: Optional[str] = None


class DefectItem(BaseModel):
    defectId: str = "DEFECT-001"
    title: str = ""
    status: str = "CONFIRMED"
    component: str = ""
    location: str = ""
    trigger: str = ""
    rootCause: str = ""
    impact: str = ""
    evidence: str = ""
    investigation: str = ""
    fix: str = ""
    confidence: str = "MEDIUM"
    severity: str = "MEDIUM"
    priority: str = "P2"


class DefectResult(BaseModel):
    defects: List[DefectItem] = Field(default_factory=list)
    summary: str = ""
    probableRootCause: str = ""
    evidence: str = ""
    suggestedInvestigation: str = ""
    suggestedFix: str = ""
    confidence: str = "MEDIUM"
    severity: str = "MEDIUM"
    priority: str = "P2"


class PublicDefectItem(BaseModel):
    defectId: str = "DEFECT-001"
    title: str = ""
    component: str = ""
    location: str = ""
    trigger: str = ""
    rootCause: str = ""
    impact: str = ""
    evidence: str = ""
    investigation: str = ""
    fix: str = ""


class PublicDefectResult(BaseModel):
    defects: List[PublicDefectItem] = Field(default_factory=list)
    summary: str = ""
    probableRootCause: str = ""
    evidence: str = ""
    suggestedInvestigation: str = ""
    suggestedFix: str = ""


class DefectAnalyzeResponse(BaseModel):
    result: PublicDefectResult
    sources: List[str] = Field(default_factory=list)
    source_details: List[SourceDto] = Field(default_factory=list)
    model: str
    prompt_version: str
    execution_time_ms: int


# ----------------------------------------------------
# Release Notes Models
# ----------------------------------------------------
class ReleaseNoteGenerateRequest(BaseModel):
    version: Optional[str] = None
    sprintInformation: str
    document_id: Optional[str] = None
    zip_document_id: Optional[str] = None


class ReleaseNoteResult(BaseModel):
    summary: str = ""
    newFeatures: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    bugFixes: List[str] = Field(default_factory=list)
    breakingChanges: List[str] = Field(default_factory=list)
    knownIssues: List[str] = Field(default_factory=list)
    technicalNotes: Optional[str] = ""


class ReleaseNoteGenerateResponse(BaseModel):
    result: ReleaseNoteResult
    sources: List[str] = Field(default_factory=list)
    source_details: List[SourceDto] = Field(default_factory=list)
    model: str
    prompt_version: str
    execution_time_ms: int


# ----------------------------------------------------
# Daily Status Models
# ----------------------------------------------------
class DailyStatusGenerateRequest(BaseModel):
    sprintInformation: str
    document_id: Optional[str] = None


class DailyStatusResult(BaseModel):
    completed: List[str] = Field(default_factory=list)
    inProgress: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    nextSteps: List[str] = Field(default_factory=list)
    importantUpdates: Optional[str] = ""


class DailyStatusGenerateResponse(BaseModel):
    result: DailyStatusResult
    sources: List[str] = Field(default_factory=list)
    source_details: List[SourceDto] = Field(default_factory=list)
    model: str
    prompt_version: str
    execution_time_ms: int


# ----------------------------------------------------
# Health Check Models
# ----------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    service: str
    chroma: str
    gemini_configured: bool
