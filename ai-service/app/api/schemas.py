from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


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
# Health Check Models
# ----------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    service: str
    chroma: str
    gemini_configured: bool


# ----------------------------------------------------
# Mock Screens Models (BRD-Driven Dynamic UI Engine)
# ----------------------------------------------------
class DesignContext(BaseModel):
    application_type: str = "Enterprise Web Application"
    design_style: str = "enterprise"
    primary_color: str = "#1E40AF"
    secondary_color: str = "#0D9488"
    accent_color: str = "#F59E0B"
    neutral_dark: str = "#0F172A"
    neutral_light: str = "#F8FAFC"
    surface_color: str = "#FFFFFF"
    density: str = "comfortable"
    navigation_pattern: str = "sidebar_and_header"
    brand_name: str = "Enterprise Suite"


def _coerce_to_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return [str(value)]

    result = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            candidates = [
                item.get("message"),
                item.get("text"),
                item.get("title"),
                item.get("label"),
                item.get("description"),
                item.get("rule"),
                item.get("summary"),
                item.get("name"),
            ]
            chosen = next((str(c) for c in candidates if c and str(c).strip()), None)
            if chosen:
                result.append(chosen)
            else:
                formatted = ", ".join(f"{k}: {v}" for k, v in item.items() if v)
                result.append(formatted if formatted else str(item))
        elif isinstance(item, (int, float, bool)):
            result.append(str(item))
        elif item is not None:
            result.append(str(item))
    return result


class ScreenField(BaseModel):
    label: str
    type: str = "text"
    value: Optional[str] = ""
    placeholder: Optional[str] = ""
    required: bool = False
    options: List[str] = Field(default_factory=list)

    @field_validator("value", mode="before")
    @classmethod
    def coerce_display_value(cls, value):
        if isinstance(value, (bool, int, float)):
            return str(value)
        return value

    @field_validator("options", mode="before")
    @classmethod
    def coerce_options(cls, value):
        return _coerce_to_str_list(value)


class ScreenTable(BaseModel):
    title: Optional[str] = ""
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    pagination_info: Optional[str] = ""


class ScreenAction(BaseModel):
    label: str
    type: str = "primary"
    icon: Optional[str] = ""
    target: Optional[str] = ""


class HeaderStat(BaseModel):
    label: str
    value: str
    change: Optional[str] = ""
    status: Optional[str] = "normal"


class ScreenComponent(BaseModel):
    type: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    fields: List[ScreenField] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    stats: List[HeaderStat] = Field(default_factory=list)
    actions: List[ScreenAction] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    badges: List[Dict[str, str]] = Field(default_factory=list)

    @field_validator("steps", mode="before")
    @classmethod
    def coerce_steps(cls, value):
        return _coerce_to_str_list(value)

    @field_validator("badges", mode="before")
    @classmethod
    def coerce_badges(cls, value):
        if not isinstance(value, list):
            return []
        coerced = []
        for item in value:
            if isinstance(item, dict):
                coerced.append({str(k): str(v) for k, v in item.items()})
            elif isinstance(item, str):
                coerced.append({"label": item})
            elif item is not None:
                coerced.append({"label": str(item)})
        return coerced


class ScreenSpecification(BaseModel):
    screen_id: str = "SCREEN-001"
    sequence: int = 1
    name: str
    purpose: str
    user_role: str = "Enterprise User"
    screen_type: str = "dashboard"
    navigation_context: Dict[str, Any] = Field(default_factory=dict)
    header_stats: List[HeaderStat] = Field(default_factory=list)
    components: List[ScreenComponent] = Field(default_factory=list)
    fields: List[ScreenField] = Field(default_factory=list)
    tables: List[ScreenTable] = Field(default_factory=list)
    actions: List[ScreenAction] = Field(default_factory=list)
    workflow_state: Optional[str] = ""
    business_rules: List[str] = Field(default_factory=list)
    notifications: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    related_requirements: List[str] = Field(default_factory=list)
    image_prompt: Optional[str] = None

    @field_validator("business_rules", "notifications", "data_sources", "related_requirements", mode="before")
    @classmethod
    def coerce_string_lists(cls, value):
        return _coerce_to_str_list(value)

    @field_validator("workflow_state", mode="before")
    @classmethod
    def coerce_workflow_state(cls, value):
        if isinstance(value, dict):
            return value.get("state") or value.get("name") or value.get("status") or str(value)
        if value is not None and not isinstance(value, str):
            return str(value)
        return value or ""


class ScreenPlan(BaseModel):
    application_name: str
    application_summary: str
    user_roles: List[str] = Field(default_factory=list)
    design_context: DesignContext = Field(default_factory=DesignContext)
    screens: List[ScreenSpecification] = Field(default_factory=list)
    source_content_truncated: bool = False
    source_character_count: int = 0
    analyzed_character_count: int = 0

    @field_validator("user_roles", mode="before")
    @classmethod
    def coerce_user_roles(cls, value):
        return _coerce_to_str_list(value)


class MockScreenPlanRequest(BaseModel):
    document_id: Optional[str] = None
    brd_text: str
    project_name: Optional[str] = ""


class MockScreenPlanResponse(BaseModel):
    plan: ScreenPlan
    total_screens: int
    model: str
    execution_time_ms: int


class MockScreenRenderRequest(BaseModel):
    specification: ScreenSpecification
    design_context: Optional[DesignContext] = None
    prompt: Optional[str] = None


class MockScreenRenderResponse(BaseModel):
    screen_id: str
    sequence: int
    name: str
    image_base64: str
    mime_type: str = "image/png"
    width: int
    height: int
    image_prompt: Optional[str] = None


class MockScreenCompilePdfRequest(BaseModel):
    application_name: str
    project_name: Optional[str] = ""
    brd_name: Optional[str] = ""
    summary: Optional[str] = ""
    screens: List[Dict[str, Any]] = Field(default_factory=list)


class MockScreenCompilePdfResponse(BaseModel):
    pdf_base64: str
    page_count: int
    file_size_bytes: int
