from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    primary_color: str = "#EF7625"
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
    icon: Optional[str] = Field(default="", description="Optional semantic icon name from the supported icon set.")

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
    icon: Optional[str] = Field(default="", description="Optional semantic icon name from the supported icon set.")
    data_source: Optional[Literal["brd", "screen_data", "illustrative"]] = None
    note: Optional[str] = Field(default="", description="Must disclose illustrative sample values.")

    @model_validator(mode="after")
    def validate_stat_provenance(self):
        if self.data_source == "illustrative" and (
            not self.note or "illustrative" not in self.note.casefold()
        ):
            raise ValueError("Illustrative KPI values must be labeled in note.")
        return self


class ChartDataPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(description="BRD-grounded category, period, or series label.")
    value: float = Field(allow_inf_nan=False, description="Finite numeric chart value supported by the source data.")

    @field_validator("label")
    @classmethod
    def validate_label(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Chart data labels must not be empty.")
        return value

    @field_validator("value", mode="before")
    @classmethod
    def validate_numeric_value(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Chart data values must be numeric.")
        return value


class VisualizationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Business meaning of this data series.")
    unit: Optional[str] = Field(default="", description="BRD-supported unit for this dataset, when specified.")
    data: List[ChartDataPoint] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Visualization dataset names must not be empty.")
        return value


class VisualizationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    screen_id: str = Field(default="", description="Identifier of the screen that contains this visualization.")
    business_purpose: str = Field(default="", description="BRD-grounded reason this visualization belongs on the screen.")
    type: Literal["pie", "donut", "bar", "column", "line", "area", "stacked_bar", "stacked_area"]
    title: str
    description: Optional[str] = ""
    data_source: Literal["brd", "screen_data", "illustrative"]
    source_reference: Optional[str] = Field(default="", description="BRD section or data reference supporting the values.")
    datasets: List[VisualizationDataset] = Field(min_length=1)
    value_prefix: Optional[str] = ""
    value_suffix: Optional[str] = ""
    legend_position: Literal["bottom", "right", "none"] = "bottom"
    x_axis_label: Optional[str] = ""
    y_axis_label: Optional[str] = ""
    sample_data: bool = False
    note: Optional[str] = Field(default="", description="Must disclose illustrative sample data.")
    interpretation: Optional[str] = Field(default="", description="A concise interpretation supported by the displayed values.")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Visualization titles must not be empty.")
        return value

    @model_validator(mode="after")
    def validate_visualization(self):
        labels_by_dataset = [[point.label for point in dataset.data] for dataset in self.datasets]
        for labels in labels_by_dataset:
            normalized_labels = [label.casefold() for label in labels]
            if len(normalized_labels) != len(set(normalized_labels)):
                raise ValueError("Visualization category and period labels must be unique within each dataset.")
        if self.type in {"pie", "donut"}:
            if len(self.datasets) != 1:
                raise ValueError("Pie and doughnut charts require exactly one dataset.")
            points = self.datasets[0].data
            if len(points) < 2:
                raise ValueError("Pie and doughnut charts require at least two categories.")
            if any(point.value < 0 for point in points) or sum(point.value for point in points) <= 0:
                raise ValueError("Pie and doughnut charts require non-negative values with a positive total.")
        if self.type in {"line", "area"} and any(len(dataset.data) < 2 for dataset in self.datasets):
            raise ValueError(f"{self.type.title()} charts require at least two points per dataset.")
        if self.type in {"bar", "column", "line", "area"} and len(self.datasets) > 1:
            category_labels = [point.label for point in self.datasets[0].data]
            if any([point.label for point in dataset.data] != category_labels for dataset in self.datasets[1:]):
                raise ValueError("Multi-series charts must use the same ordered category labels.")
        if self.type in {"stacked_bar", "stacked_area"}:
            if len(self.datasets) < 2:
                raise ValueError(f"{self.type.replace('_', ' ').title()} charts require at least two datasets.")
            category_labels = [point.label for point in self.datasets[0].data]
            if any([point.label for point in dataset.data] != category_labels for dataset in self.datasets[1:]):
                raise ValueError("Stacked chart datasets must use the same ordered category labels.")
            if any(point.value < 0 for dataset in self.datasets for point in dataset.data):
                raise ValueError("Stacked chart values must be non-negative.")
        dataset_names = [dataset.name.casefold() for dataset in self.datasets]
        if len(dataset_names) != len(set(dataset_names)):
            raise ValueError("Visualization dataset names must be unique.")
        units = {dataset.unit.strip().casefold() for dataset in self.datasets if dataset.unit and dataset.unit.strip()}
        if len(units) > 1:
            raise ValueError("Datasets in one visualization must use compatible units.")
        if self.data_source == "illustrative":
            if not self.sample_data or not self.note or "illustrative" not in self.note.casefold():
                raise ValueError("Illustrative data must be marked as sample_data and labeled in note.")
        elif self.sample_data:
            raise ValueError("sample_data must be true only when data_source is illustrative.")
        return self


class ScreenComponent(BaseModel):
    type: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    icon: Optional[str] = Field(default="", description="Optional semantic icon name from the supported icon set.")
    fields: List[ScreenField] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    stats: List[HeaderStat] = Field(default_factory=list)
    actions: List[ScreenAction] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    badges: List[Dict[str, str]] = Field(default_factory=list)
    visualization: Optional[VisualizationSpec] = Field(
        default=None,
        description="Domain-independent analytical visualization specification. Prefer this over legacy chart fields.",
    )
    chart_type: Optional[Literal["pie", "donut", "bar", "column", "line", "area", "stacked_bar", "stacked_area"]] = Field(
        default=None,
        description="Legacy chart field; new plans should use visualization.",
    )
    chart_data: List[ChartDataPoint] = Field(
        default_factory=list,
        description="Only BRD-stated or explicitly available values; illustrative samples require explicit labeling.",
    )
    chart_note: Optional[str] = Field(default="", description="Clearly identify illustrative chart data when used.")
    chart_data_source: Optional[Literal["brd", "screen_data", "illustrative"]] = Field(
        default=None,
        description="Whether values come from the BRD, another explicit screen dataset, or labeled illustrative samples.",
    )
    chart_value_prefix: Optional[str] = Field(default="", description="Explicit source unit prefix such as a currency symbol.")
    chart_value_suffix: Optional[str] = Field(default="", description="Explicit source unit suffix such as a percent sign or unit.")
    progress_value: Optional[float] = Field(default=None, ge=0, le=100, description="A source-supported completion percentage.")
    progress_label: Optional[str] = Field(default="", description="BRD-grounded label for a progress indicator.")
    progress_data_source: Optional[Literal["brd", "screen_data", "illustrative"]] = Field(
        default=None,
        description="Provenance for progress_value.",
    )
    progress_note: Optional[str] = Field(default="", description="Must clearly label illustrative progress values.")

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

    @model_validator(mode="after")
    def validate_chart(self):
        if self.visualization is not None:
            if self.chart_type and self.chart_type != self.visualization.type:
                raise ValueError("chart_type must match visualization.type.")
            if self.chart_data and self.chart_data != self.visualization.datasets[0].data:
                raise ValueError("chart_data must match the first visualization dataset when both are supplied.")
            self.chart_type = self.visualization.type
            self.chart_data = self.visualization.datasets[0].data
            if not self.title:
                self.title = self.visualization.title
            if not self.description:
                self.description = self.visualization.description or ""
            self.chart_note = self.visualization.note or self.chart_note
            self.chart_data_source = self.visualization.data_source
            self.chart_value_prefix = self.visualization.value_prefix or self.chart_value_prefix
            self.chart_value_suffix = self.visualization.value_suffix or self.chart_value_suffix
        if self.chart_type is None and self.chart_data:
            raise ValueError("chart_data requires chart_type.")
        if self.chart_type is not None and not self.chart_data:
            raise ValueError(f"{self.chart_type} chart requires chart_data.")
        if self.chart_type in {"line", "area"} and len(self.chart_data) < 2:
            raise ValueError(f"{self.chart_type.title()} charts require at least two data points.")
        if self.chart_type in {"stacked_bar", "stacked_area"} and self.visualization is None:
            raise ValueError(f"{self.chart_type.replace('_', ' ').title()} charts require visualization datasets.")
        if self.chart_type in {"pie", "donut"}:
            if len(self.chart_data) < 2:
                raise ValueError("Pie charts require at least two categories.")
            if any(point.value < 0 for point in self.chart_data) or sum(point.value for point in self.chart_data) <= 0:
                raise ValueError("Pie charts require non-negative values with a positive total.")
        if self.chart_data_source == "illustrative" and (
            not self.chart_note or "illustrative" not in self.chart_note.casefold()
        ):
            raise ValueError("Illustrative chart data must be labeled in chart_note.")
        if self.chart_type and self.visualization is None:
            legacy_data_source = self.chart_data_source or "screen_data"
            self.visualization = VisualizationSpec(
                type=self.chart_type,
                title=self.title or self.type,
                description=self.description,
                data_source=legacy_data_source,
                datasets=[VisualizationDataset(name=self.title or "Series 1", data=self.chart_data)],
                value_prefix=self.chart_value_prefix,
                value_suffix=self.chart_value_suffix,
                sample_data=legacy_data_source == "illustrative",
                note=self.chart_note,
            )
        if self.progress_value is None and (
            self.progress_label or self.progress_data_source or self.progress_note
        ):
            raise ValueError("Progress labels and provenance require progress_value.")
        if self.progress_value is not None and not self.progress_data_source:
            raise ValueError("Progress indicators require progress_data_source.")
        if self.progress_data_source == "illustrative" and (
            not self.progress_note or "illustrative" not in self.progress_note.casefold()
        ):
            raise ValueError("Illustrative progress data must be labeled in progress_note.")
        return self


class ScreenEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = "EVT-001"
    type: str = "submit"  # click, submit, select, cancel, filter, navigate
    label: str
    trigger_component: Optional[str] = None
    business_rule_refs: List[str] = Field(default_factory=list)

    @field_validator("business_rule_refs", mode="before")
    @classmethod
    def coerce_rules(cls, value):
        return _coerce_to_str_list(value)


class NavigationFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_event: str
    to_screen_id: str
    condition: Optional[str] = "always"
    label: Optional[str] = None


class DataBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    entity: str
    attribute: Optional[str] = None
    binding_type: Optional[str] = "read_write"  # read, write, read_write


class ScreenInteraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: List[ScreenEvent] = Field(default_factory=list)
    navigation_flows: List[NavigationFlow] = Field(default_factory=list)
    data_bindings: List[DataBinding] = Field(default_factory=list)
    validation_rules: List[str] = Field(default_factory=list)

    @field_validator("validation_rules", mode="before")
    @classmethod
    def coerce_val_rules(cls, value):
        return _coerce_to_str_list(value)


class GlobalNavigationGraphEdge(BaseModel):
    from_screen_id: str
    to_screen_id: str
    event: Optional[str] = None
    condition: Optional[str] = "always"
    label: Optional[str] = None


class SharedWorkflow(BaseModel):
    id: str
    name: str
    screens: List[str] = Field(default_factory=list)
    description: Optional[str] = ""

    @field_validator("screens", mode="before")
    @classmethod
    def coerce_wf_screens(cls, value):
        return _coerce_to_str_list(value)


class GlobalNavigation(BaseModel):
    entry_screen: Optional[str] = None
    navigation_graph: List[GlobalNavigationGraphEdge] = Field(default_factory=list)
    data_entities: List[str] = Field(default_factory=list)
    shared_workflows: List[SharedWorkflow] = Field(default_factory=list)

    @field_validator("data_entities", mode="before")
    @classmethod
    def coerce_entities(cls, value):
        return _coerce_to_str_list(value)


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
    interaction: Optional[ScreenInteraction] = None
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

    @model_validator(mode="after")
    def attach_visualization_context(self):
        signatures = set()
        for component in self.components:
            visualization = component.visualization
            if visualization is None:
                continue
            if self.screen_type.strip().casefold().replace("-", "_") in {
                "login", "profile", "form", "create_form", "edit_form", "data_entry", "confirmation",
            }:
                raise ValueError(
                    f"Screen type '{self.screen_type}' is not appropriate for analytical visualizations."
                )
            if visualization.screen_id and visualization.screen_id != self.screen_id:
                raise ValueError("Visualization screen_id must match its containing screen.")
            visualization.screen_id = self.screen_id
            if not visualization.business_purpose.strip():
                visualization.business_purpose = self.purpose
            signature = (
                visualization.type,
                tuple(
                    tuple((point.label.casefold(), point.value) for point in dataset.data)
                    for dataset in visualization.datasets
                ),
            )
            if signature in signatures:
                raise ValueError("A screen cannot contain duplicate visualizations with the same data.")
            signatures.add(signature)
        return self


class ScreenPlan(BaseModel):
    application_name: str
    application_summary: str
    user_roles: List[str] = Field(default_factory=list)
    design_context: DesignContext = Field(default_factory=DesignContext)
    screens: List[ScreenSpecification] = Field(default_factory=list)
    global_navigation: Optional[GlobalNavigation] = None
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


class MockScreenWireframeRequest(BaseModel):
    specification: ScreenSpecification
    design_context: Optional[DesignContext] = None


class MockScreenWireframeResponse(BaseModel):
    screen_id: str
    sequence: int
    name: str
    wireframe_base64: str
    mime_type: str = "image/png"
    width: int
    height: int


class ScreenExplanationField(BaseModel):
    name: str
    type: Optional[str] = "text"
    required: Optional[bool] = False
    rule: Optional[str] = ""


class ScreenExplanationSection(BaseModel):
    title: str
    description: Optional[str] = ""
    fields: List[ScreenExplanationField] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    notes: Optional[str] = ""

    @field_validator("columns", mode="before")
    @classmethod
    def coerce_columns(cls, value):
        return _coerce_to_str_list(value)


class ScreenExplanationAction(BaseModel):
    label: str
    type: Optional[str] = "primary"
    outcome: Optional[str] = ""


class ScreenExplanation(BaseModel):
    purpose_summary: str
    sections: List[ScreenExplanationSection] = Field(default_factory=list)
    actions: List[ScreenExplanationAction] = Field(default_factory=list)
    validation_rules: List[str] = Field(default_factory=list)
    navigation_flow: Optional[str] = ""
    brd_references: List[str] = Field(default_factory=list)

    @field_validator("validation_rules", "brd_references", mode="before")
    @classmethod
    def coerce_explanation_lists(cls, value):
        return _coerce_to_str_list(value)


class MockScreenExplainRequest(BaseModel):
    specification: ScreenSpecification
    brd_excerpt: Optional[str] = ""
    project_name: Optional[str] = ""


class MockScreenExplainResponse(BaseModel):
    screen_id: str
    sequence: int
    name: str
    explanation: ScreenExplanation


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
