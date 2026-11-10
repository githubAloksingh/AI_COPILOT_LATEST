import base64
import io
import pytest
import pymupdf
from PIL import Image

from app.api.schemas import (
    DesignContext,
    ScreenComponent,
    ScreenAction,
    ScreenField,
    ScreenInteraction,
    ScreenSpecification,
)
from app.services.html_screen_renderer import HtmlScreenRenderer
from app.services.image_generation_service import ImageGenerationService
from app.services.pdf_compilation_service import pdf_compilation_service


def _png_bytes(width=1024, height=576):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color="#f4a261").save(buffer, format="PNG")
    return buffer.getvalue()


def _spec():
    return ScreenSpecification(
        screen_id="SCREEN-HEALTH-01",
        sequence=1,
        name="Referral intake",
        purpose="Capture a new referral for clinical review.",
        user_role="Care coordinator",
        screen_type="create_form",
        fields=[
            ScreenField(label="Patient identifier", required=True, value="<private-value>"),
            ScreenField(label="Referral reason", type="textarea"),
        ],
        actions=[ScreenAction(label="Submit referral", type="primary")],
    )


class CapturingHtmlRenderer:
    def __init__(self, screenshot=None):
        self.screenshot = screenshot or _png_bytes()
        self.spec = None
        self.design = None

    def render(self, spec, design):
        self.spec = spec
        self.design = design
        return self.screenshot


def test_html_renderer_adds_contextual_icons_to_fields_cards_stats_and_actions():
    spec = ScreenSpecification(
        screen_id="SCREEN-ICON-01",
        sequence=1,
        name="Service operations",
        purpose="Review service performance and add a new case.",
        screen_type="dashboard",
        header_stats=[
            {"label": "Open cases", "value": "24", "icon": "clipboard"},
        ],
        fields=[
            ScreenField(label="Assigned user", icon="user"),
        ],
        components=[
            ScreenComponent(
                type="kpi_grid",
                title="Performance",
                icon="chart",
                stats=[{"label": "Resolved", "value": "18", "icon": "check"}],
                actions=[ScreenAction(label="Add case", icon="plus")],
            )
        ],
        actions=[ScreenAction(label="View report", icon="trend-up")],
    )

    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert 'class="field-label"><svg' in document
    assert 'class="panel-title"><svg' in document
    assert 'class="panel-art"' not in document
    assert 'aria-hidden="true"' in document
    assert "Add case</button>" in document
    assert "View report</button>" in document
    assert document.count("<svg") >= 6
    with Image.open(io.BytesIO(HtmlScreenRenderer().render(spec, DesignContext()))) as image:
        assert image.width == 1600
        assert image.height >= 900


def test_unrecognized_icon_name_is_ignored_without_rendering_untrusted_svg():
    spec = ScreenSpecification(
        screen_id="SCREEN-ICON-02",
        sequence=1,
        name="Profile",
        purpose="Update profile.",
        screen_type="profile",
        actions=[ScreenAction(label="Save", icon='<svg onload="alert(1)">')],
    )

    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert "<svg onload=" not in document
    assert 'class="primary"' in document


def test_html_renderer_omits_requirements_navigation_and_interactions_sections():
    spec = ScreenSpecification(
        screen_id="SCREEN-DETAIL-01",
        sequence=1,
        name="Overdraft tracker",
        purpose="Review overdraft accounts.",
        screen_type="dashboard",
        business_rules=["Overdrafts over 7 days require review."],
        notifications=["Email the compliance team."],
        interaction=ScreenInteraction(
            events=[
                {
                    "label": "Open Overdraft Tracker",
                    "type": "click",
                    "trigger_component": "table",
                }
            ],
            navigation_flows=[
                {"from_event": "Open Overdraft Tracker", "to_screen_id": "SCREEN-003"}
            ],
            validation_rules=["Account ID is required."],
        ),
    )

    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert "Requirements and guidance" not in document
    assert "Navigation flow" not in document
    assert "Available interactions" not in document
    assert "Overdrafts over 7 days require review." not in document
    assert "SCREEN-003" not in document
    assert "Open Overdraft Tracker" not in document


def test_progress_indicator_requires_grounded_provenance_and_renders_accessible_value():
    with pytest.raises(ValueError, match="progress_data_source"):
        ScreenComponent(type="progress", progress_value=45)

    with pytest.raises(ValueError, match="Illustrative progress"):
        ScreenComponent(
            type="progress",
            progress_value=45,
            progress_data_source="illustrative",
        )

    spec = ScreenSpecification(
        screen_id="SCREEN-PROGRESS-01",
        sequence=1,
        name="Application review",
        purpose="Track review completion.",
        screen_type="workflow",
        components=[
            ScreenComponent(
                type="workflow_stepper",
                title="Review completion",
                progress_value=60,
                progress_label="Review complete",
                progress_data_source="screen_data",
            )
        ],
    )

    document = HtmlScreenRenderer().build_document(spec, DesignContext())
    assert 'role="progressbar"' in document
    assert 'aria-valuenow="60"' in document
    assert "Review complete" in document
    assert "60%" in document
    with Image.open(io.BytesIO(HtmlScreenRenderer().render(spec, DesignContext()))) as image:
        assert image.size == (1600, 900)


def test_login_renders_with_local_decorative_styling_and_no_artwork():
    spec = ScreenSpecification(
        screen_id="SCREEN-LOGIN-01",
        sequence=1,
        name="Sign in",
        purpose="Authenticate to the service portal.",
        screen_type="login",
    )

    renderer = HtmlScreenRenderer()
    document = renderer.build_document(spec, DesignContext())
    screenshot = renderer.render(spec, DesignContext())

    assert 'class="login-art"' in document
    assert 'class="brand-icon"' in document
    assert 'class="illustration-badge" aria-hidden="true"' in document
    assert "linear-gradient" in document
    assert "<img" not in document
    with Image.open(io.BytesIO(screenshot)) as image:
        assert image.size == (1600, 900)


def test_image_generation_uses_html_renderer_without_artwork(monkeypatch):
    monkeypatch.setenv("MOCK_SCREEN_RENDERER", "html")
    renderer = CapturingHtmlRenderer()
    service = ImageGenerationService(renderer)
    spec = _spec()

    output = service.generate_screen_image(spec, DesignContext())

    assert output == renderer.screenshot
    assert renderer.spec is spec
    assert renderer.design is not None
    assert "Referral intake" in spec.image_prompt


def test_multiple_html_screens_render_without_artwork_and_compile_pdf(monkeypatch):
    monkeypatch.setenv("MOCK_SCREEN_RENDERER", "html")
    service = ImageGenerationService()
    design = DesignContext()
    screens = [
        ScreenSpecification(
            screen_id="SCREEN-FORM-01",
            sequence=1,
            name="Referral intake",
            purpose="Capture a referral.",
            screen_type="create_form",
            fields=[ScreenField(label="Patient identifier", required=True)],
            actions=[ScreenAction(label="Submit", type="primary")],
        ),
        ScreenSpecification(
            screen_id="SCREEN-DASHBOARD-01",
            sequence=2,
            name="Service overview",
            purpose="Review service outcomes.",
            screen_type="dashboard",
            components=[ScreenComponent(
                type="chart",
                title="Outcome distribution",
                chart_type="donut",
                chart_data=[{"label": "Completed", "value": 12}, {"label": "Pending", "value": 5}],
            )],
        ),
        ScreenSpecification(
            screen_id="SCREEN-TABLE-01",
            sequence=3,
            name="Referral queue",
            purpose="Review queued referrals.",
            screen_type="work_queue",
            tables=[{"columns": ["Reference", "Status"], "rows": [{"Reference": "R-101", "Status": "Pending"}]}],
        ),
    ]

    images = [service.generate_screen_image(spec, design) for spec in screens]
    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Referral Management",
        project_name=None,
        brd_name="Regression BRD",
        summary="Local rendering regression.",
        screens=[
            {
                "sequence": spec.sequence,
                "name": spec.name,
                "screen_type": spec.screen_type,
                "purpose": spec.purpose,
                "image_base64": base64.b64encode(image).decode("ascii"),
            }
            for spec, image in zip(screens, images)
        ],
    )

    for image in images:
        with Image.open(io.BytesIO(image)) as rendered:
            assert rendered.size == (1600, 900)
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        assert document.page_count >= len(screens) + 1
        assert sum(bool(page.get_images()) for page in document) >= len(screens)



def test_html_renderer_preserves_exact_screen_text_and_contextual_structure():
    spec = _spec()
    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert "Referral intake" in document
    assert "Capture a new referral for clinical review." in document
    assert "Patient identifier" in document
    assert "&lt;private-value&gt;" in document
    assert "Submit referral" in document
    assert 'class="app form"' in document


@pytest.mark.parametrize(
    ("chart_type", "expected_svg"),
    [
        ("pie", 'aria-label="Pie chart"'),
        ("donut", 'aria-label="Donut chart"'),
        ("bar", 'aria-label="Bar chart"'),
        ("line", 'aria-label="Line chart"'),
    ],
)
def test_html_renderer_renders_branded_charts_from_specified_data(chart_type, expected_svg):
    spec = ScreenSpecification(
        screen_id="SCREEN-ANALYTICS-01",
        sequence=1,
        name="Service analytics",
        purpose="Review service outcomes over time.",
        screen_type="analytics",
        components=[
            ScreenComponent(
                type="chart",
                title="Outcome distribution",
                chart_type=chart_type,
                chart_data=[
                    {"label": "Completed", "value": 12},
                    {"label": "Pending", "value": 5},
                ],
                chart_data_source="illustrative",
                chart_note="Illustrative data",
            )
        ],
    )

    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert expected_svg in document
    assert "Completed" in document
    assert "Pending" in document
    assert "Illustrative data" in document
    assert 'class="panel chart-panel single-chart"' in document
    if chart_type == "bar":
        assert 'role="img" aria-label="Bar chart"' in document
    if chart_type in {"pie", "donut"}:
        assert "70.6%" in document


def test_chart_labels_are_html_escaped_and_incomplete_chart_data_is_rejected():
    renderer = HtmlScreenRenderer()
    spec = ScreenSpecification(
        screen_id="SCREEN-ANALYTICS-02",
        sequence=1,
        name="Analytics",
        purpose="Compare categories.",
        screen_type="report",
        components=[
            ScreenComponent(
                type="chart",
                chart_type="bar",
                chart_data=[{"label": "<script>", "value": 2}],
            )
        ],
    )
    document = renderer.build_document(spec, DesignContext())
    assert "&lt;script&gt;" in document
    assert "<script>" not in document

    with pytest.raises(ValueError, match="requires chart_data"):
        ScreenComponent(type="chart", chart_type="pie")


@pytest.mark.parametrize(
    ("chart_type", "chart_data", "source", "note", "message"),
    [
        ("line", [{"label": "Only", "value": 1}], None, "", "at least two data points"),
        ("pie", [{"label": "Only", "value": 1}], None, "", "at least two categories"),
        (
            "pie",
            [{"label": "Refund", "value": -1}, {"label": "Paid", "value": 2}],
            None,
            "",
            "non-negative values",
        ),
        (
            "pie",
            [{"label": "Empty A", "value": 0}, {"label": "Empty B", "value": 0}],
            None,
            "",
            "positive total",
        ),
        (
            "bar",
            [{"label": "Sample", "value": 2}],
            "illustrative",
            "",
            "labeled in chart_note",
        ),
    ],
)
def test_chart_schema_rejects_ambiguous_or_misleading_data(
    chart_type, chart_data, source, note, message
):
    with pytest.raises(ValueError, match=message):
        ScreenComponent(
            type="chart",
            chart_type=chart_type,
            chart_data=chart_data,
            chart_data_source=source,
            chart_note=note,
        )


def test_bar_chart_displays_negative_values_on_the_opposite_side_of_zero():
    spec = ScreenSpecification(
        screen_id="SCREEN-ANALYTICS-04",
        sequence=1,
        name="Financial summary",
        purpose="Compare income and expenses.",
        screen_type="report",
        components=[
            ScreenComponent(
                type="chart",
                chart_type="bar",
                chart_data=[
                    {"label": "Income", "value": 120},
                    {"label": "Expense", "value": -80},
                ],
                chart_value_prefix="$",
            )
        ],
    )
    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert "$120" in document
    assert "-$80" in document
    assert "right:16.67%" in document
    assert "left:50%" in document


@pytest.mark.parametrize("chart_type", ["pie", "bar", "line"])
def test_html_renderer_renders_each_chart_type_in_chromium(chart_type):
    spec = ScreenSpecification(
        screen_id="SCREEN-ANALYTICS-03",
        sequence=1,
        name="Trend analysis",
        purpose="Review outcome trends.",
        screen_type="report",
        components=[
            ScreenComponent(
                type="chart",
                chart_type=chart_type,
                chart_data=[
                    {"label": "Q1", "value": 8},
                    {"label": "Q2", "value": 13},
                    {"label": "Q3", "value": 11},
                ],
                chart_value_suffix=" cases",
            )
        ],
    )

    screenshot = HtmlScreenRenderer().render(spec, DesignContext())

    with Image.open(io.BytesIO(screenshot)) as image:
        assert image.size == (1600, 900)
        assert image.getbbox() == (0, 0, 1600, 900)

    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Analytics",
        project_name=None,
        brd_name=None,
        summary="Validate generated chart delivery.",
        screens=[
            {
                "sequence": 1,
                "name": spec.name,
                "screen_type": spec.screen_type,
                "purpose": spec.purpose,
                "components": [component.model_dump() for component in spec.components],
                "image_base64": base64.b64encode(screenshot).decode("ascii"),
            }
        ],
    )
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        assert any(page.get_images() for page in document)


def test_pdf_metadata_reports_local_html_renderer():
    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Referral Management",
        project_name=None,
        brd_name=None,
        summary="Referral workflow screens.",
        screens=[
            {
                "sequence": 1,
                "name": "Referral intake",
                "image_base64": base64.b64encode(_png_bytes()).decode("ascii"),
            }
        ],
    )
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        assert "Chromium HTML/CSS renderer" in document.metadata["creator"]
        assert "CSS backgrounds and inline SVG" in document.metadata["subject"]
