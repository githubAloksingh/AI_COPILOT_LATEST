import base64
import io
from importlib import import_module
import os

import httpx
import pytest
import pymupdf
from PIL import Image
from PIL import ImageChops
from pydantic import ValidationError

from app.api.schemas import (
    DesignContext,
    ScreenComponent,
    ScreenAction,
    ScreenField,
    ScreenSpecification,
)
from app.config import settings
from app.services.html_screen_renderer import HtmlScreenRenderer
from app.services.image_generation_service import ImageGenerationError, ImageGenerationService
from app.services.pdf_compilation_service import pdf_compilation_service
from app.services.screen_plan_service import ScreenPlanService

image_generation_module = import_module("app.services.image_generation_service")


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
        self.asset = None
        self.spec = None

    def classify_layout(self, spec):
        return "form"

    def render(self, spec, design, visual_asset=None):
        self.spec = spec
        self.asset = visual_asset
        return self.screenshot


def _stability_service(monkeypatch, tmp_path, renderer=None):
    monkeypatch.setenv("IMAGE_GENERATOR_PROVIDER", "stability")
    service = ImageGenerationService(renderer or CapturingHtmlRenderer())
    service.api_key = "unit-test-key"
    service.asset_dir = tmp_path
    return service


def _response(status_code=200, *, content=None, content_type="image/png"):
    return httpx.Response(
        status_code,
        headers={"content-type": content_type},
        content=_png_bytes() if content is None else content,
        request=httpx.Request("POST", "https://api.stability.ai/test"),
    )


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

    document = HtmlScreenRenderer().build_document(spec, DesignContext(), _png_bytes())

    assert 'class="field-label"><svg' in document
    assert 'class="panel-title"><svg' in document
    assert 'class="panel-art"' in document
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


def test_login_uses_decorative_illustration_slot_and_professional_brand_icon():
    spec = ScreenSpecification(
        screen_id="SCREEN-LOGIN-01",
        sequence=1,
        name="Sign in",
        purpose="Authenticate to the service portal.",
        screen_type="login",
    )
    asset = _png_bytes()

    document = HtmlScreenRenderer().build_document(spec, DesignContext(), asset)

    assert 'class="login-art"' in document
    assert 'class="asset"' in document
    assert 'class="brand-icon"' in document
    assert 'class="illustration-badge" aria-hidden="true"' in document


def test_stability_asset_is_used_only_as_art_and_saved_for_reuse(monkeypatch, tmp_path):
    renderer = CapturingHtmlRenderer()
    service = _stability_service(monkeypatch, tmp_path, renderer)
    captured = {}
    asset = _png_bytes()

    def fake_post(url, *, headers, files, timeout):
        captured.update(url=url, headers=headers, files=files, timeout=timeout)
        return _response(content=asset)

    monkeypatch.setattr(image_generation_module.httpx, "post", fake_post)
    spec = _spec()

    output = service.generate_screen_image(spec, DesignContext())

    assert output == renderer.screenshot
    assert renderer.asset == asset
    assert captured["headers"]["Authorization"] == "Bearer unit-test-key"
    assert captured["timeout"] == service.timeout_seconds
    assert "private-value" not in captured["files"]["prompt"][1]
    assert "Patient identifier" not in captured["files"]["prompt"][1]
    assert "Do not include any text" in captured["files"]["prompt"][1]
    stored_assets = list(tmp_path.glob("form-*.png"))
    assert len(stored_assets) == 1
    stored = stored_assets[0]
    assert stored.read_bytes() == asset

    second_renderer = CapturingHtmlRenderer()
    second_service = _stability_service(monkeypatch, tmp_path, second_renderer)
    monkeypatch.setattr(
        image_generation_module.httpx,
        "post",
        lambda *args, **kwargs: pytest.fail("A stored asset should be reused."),
    )
    second_service.generate_screen_image(_spec(), DesignContext())
    assert second_renderer.asset == asset


def test_stability_asset_prompt_and_cache_are_specific_to_domain_context(monkeypatch, tmp_path):
    service = _stability_service(monkeypatch, tmp_path)
    prompts = []

    def fake_post(url, *, headers, files, timeout):
        prompts.append(files["prompt"][1])
        return _response()

    monkeypatch.setattr(image_generation_module.httpx, "post", fake_post)
    service.generate_screen_image(_spec(), DesignContext(application_type="Healthcare referral portal"))
    service.generate_screen_image(_spec(), DesignContext(application_type="Inventory management system"))

    assert len(prompts) == 2
    assert "Healthcare referral portal" in prompts[0]
    assert "Inventory management system" in prompts[1]
    assert prompts[0] != prompts[1]
    assert "Patient identifier" not in prompts[0]
    assert "Do not include any text" in prompts[0]
    assert len(list(tmp_path.glob("form-*.png"))) == 2


def test_stability_provider_requires_key_and_does_not_fall_back(monkeypatch, tmp_path):
    renderer = CapturingHtmlRenderer()
    service = _stability_service(monkeypatch, tmp_path, renderer)
    service.api_key = ""
    monkeypatch.setattr(
        image_generation_module.httpx,
        "post",
        lambda *args, **kwargs: pytest.fail("No request should be sent without a key."),
    )

    with pytest.raises(ImageGenerationError, match="STABILITY_API_KEY is required") as exc:
        service.generate_screen_image(_spec())

    assert exc.value.status_code == 503
    assert renderer.asset is None


@pytest.mark.parametrize(
    ("status_code", "message", "expected_status"),
    [
        (401, "rejected the configured API key", 401),
        (403, "rejected the configured API key", 403),
        (429, "rate limit", 429),
        (500, "HTTP 500", 502),
    ],
)
def test_stability_upstream_statuses_are_reported_without_fallback(
    monkeypatch,
    tmp_path,
    status_code,
    message,
    expected_status,
):
    renderer = CapturingHtmlRenderer()
    service = _stability_service(monkeypatch, tmp_path, renderer)
    monkeypatch.setattr(
        image_generation_module.httpx,
        "post",
        lambda *args, **kwargs: _response(status_code),
    )

    with pytest.raises(ImageGenerationError, match=message) as exc:
        service.generate_screen_image(_spec())

    assert exc.value.status_code == expected_status
    assert renderer.asset is None
    assert not list(tmp_path.glob("*.png"))


def test_stability_insufficient_credits_renders_without_artwork_and_stops_retrying(
    monkeypatch,
    tmp_path,
):
    renderer = CapturingHtmlRenderer()
    service = _stability_service(monkeypatch, tmp_path, renderer)
    calls = []

    def insufficient_credits(*args, **kwargs):
        calls.append(True)
        return _response(402)

    monkeypatch.setattr(image_generation_module.httpx, "post", insufficient_credits)

    first_image = service.generate_screen_image(_spec())
    second_image = service.generate_screen_image(_spec())

    assert first_image == renderer.screenshot
    assert second_image == renderer.screenshot
    assert renderer.asset is None
    assert len(calls) == 1
    assert not list(tmp_path.glob("*.png"))


def test_stability_timeout_and_connection_errors_are_explicit(monkeypatch, tmp_path):
    service = _stability_service(monkeypatch, tmp_path)
    monkeypatch.setattr(
        image_generation_module.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.TimeoutException("timeout")),
    )

    with pytest.raises(ImageGenerationError, match="timed out") as timeout_error:
        service.generate_screen_image(_spec())
    assert timeout_error.value.status_code == 504

    request = httpx.Request("POST", service.api_url)
    monkeypatch.setattr(
        image_generation_module.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("unavailable", request=request)),
    )
    with pytest.raises(ImageGenerationError, match="Could not connect") as connection_error:
        service.generate_screen_image(_spec())
    assert connection_error.value.status_code == 502


@pytest.mark.parametrize(
    ("content_type", "content", "message"),
    [
        ("application/json", b'{"error":"not an image"}', "non-PNG response"),
        ("image/png", b"invalid image bytes", "invalid or unreadable PNG"),
        ("image/png", _png_bytes(320, 320), "low-resolution PNG"),
    ],
)
def test_stability_rejects_non_png_invalid_and_low_resolution_assets(
    monkeypatch,
    tmp_path,
    content_type,
    content,
    message,
):
    service = _stability_service(monkeypatch, tmp_path)
    monkeypatch.setattr(
        image_generation_module.httpx,
        "post",
        lambda *args, **kwargs: _response(content=content, content_type=content_type),
    )

    with pytest.raises(ImageGenerationError, match=message):
        service.generate_screen_image(_spec())


def test_explicit_pymupdf_fallback_runs_without_stability(monkeypatch):
    monkeypatch.setenv("IMAGE_GENERATOR_PROVIDER", "pymupdf")
    service = ImageGenerationService()
    spec = _spec()
    expected = _png_bytes()
    monkeypatch.setattr(service, "_render_enterprise_mockup", lambda spec, design: expected)
    monkeypatch.setattr(
        image_generation_module.httpx,
        "post",
        lambda *args, **kwargs: pytest.fail("PyMuPDF selection must not call Stability."),
    )

    assert service.generate_screen_image(spec) == expected
    assert service.renderer_name == "PyMuPDF Native Engine"
    assert service.visual_asset_provider == "Not used"


def test_html_renderer_preserves_exact_screen_text_and_contextual_structure():
    spec = _spec()
    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert "Referral intake" in document
    assert "Capture a new referral for clinical review." in document
    assert "Patient identifier" in document
    assert "&lt;private-value&gt;" in document
    assert "Submit referral" in document
    assert 'class="app form"' in document
    assert "https://api.stability.ai" not in document


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


def test_visualization_spec_provenance_math_and_screen_context_are_validated():
    component = ScreenComponent(
        type="visualization",
        visualization={
            "type": "donut",
            "title": "Appointment outcomes",
            "business_purpose": "Review outcomes required by the BRD.",
            "data_source": "brd",
            "source_reference": "BRD reporting requirement 4.2",
            "datasets": [{
                "name": "Appointments",
                "data": [{"label": "Completed", "value": 18}, {"label": "Rescheduled", "value": 6}],
            }],
            "legend_position": "right",
        },
    )
    screen = ScreenSpecification(
        screen_id="SCREEN-APPOINTMENTS",
        name="Appointment analysis",
        purpose="Review appointment outcomes.",
        screen_type="report",
        components=[component],
    )
    document = HtmlScreenRenderer().build_document(screen, DesignContext())

    assert component.visualization.screen_id == "SCREEN-APPOINTMENTS"
    assert component.visualization.business_purpose == "Review outcomes required by the BRD."
    assert "Total" in document
    assert "24" in document
    assert "75.0%" in document
    assert "BRD reporting requirement 4.2" in document

    with pytest.raises(ValidationError, match="Illustrative data"):
        ScreenComponent(
            type="visualization",
            visualization={
                "type": "bar",
                "title": "Unlabeled sample",
                "data_source": "illustrative",
                "datasets": [{"name": "Series", "data": [{"label": "A", "value": 2}]}],
            },
        )

    with pytest.raises(ValidationError, match="same ordered category labels"):
        ScreenComponent(
            type="visualization",
            visualization={
                "type": "stacked_bar",
                "title": "Misaligned series",
                "data_source": "illustrative",
                "sample_data": True,
                "note": "Illustrative data only",
                "datasets": [
                    {"name": "A", "data": [{"label": "Week 1", "value": 2}]},
                    {"name": "B", "data": [{"label": "Week 2", "value": 3}]},
                ],
            },
        )


@pytest.mark.parametrize("chart_type", ["area", "stacked_bar", "stacked_area"])
def test_structured_area_and_stacked_charts_render_to_pdf(chart_type):
    datasets = [
        {"name": "Station A", "data": [{"label": "Week 1", "value": 12}, {"label": "Week 2", "value": 18}]},
        {"name": "Station B", "data": [{"label": "Week 1", "value": 7}, {"label": "Week 2", "value": 9}]},
    ]
    if chart_type == "area":
        datasets = datasets[:1]
    component = ScreenComponent(
        type="visualization",
        visualization={
            "type": chart_type,
            "title": "Acoustic detections",
            "description": "Compare event detections over observation weeks.",
            "business_purpose": "Identify station activity patterns.",
            "data_source": "illustrative",
            "source_reference": "Illustrative planning example",
            "datasets": datasets,
            "value_suffix": " events",
            "legend_position": "right",
            "x_axis_label": "Observation week",
            "y_axis_label": "Event count",
            "sample_data": True,
            "note": "Illustrative sample data—not actual results",
            "interpretation": "Compare values across periods and stations.",
        },
    )
    spec = ScreenSpecification(
        screen_id="SCREEN-ACOUSTICS",
        sequence=1,
        name="Acoustic analysis",
        purpose="Review observation trends.",
        screen_type="report",
        components=[component],
    )
    renderer = HtmlScreenRenderer()
    document = renderer.build_document(spec, DesignContext())

    assert "Acoustic detections" in document
    assert "Illustrative sample data—not actual results" in document
    if chart_type != "stacked_bar":
        assert "Observation week" in document
        assert "Event count" in document
    if chart_type == "stacked_bar":
        assert "chart-stack-track" in document
    else:
        assert "<svg" in document
        assert "fill-opacity" in document if chart_type in {"area", "stacked_area"} else True

    screenshot = renderer.render(spec, DesignContext())
    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Acoustic Observatory",
        project_name=None,
        brd_name=None,
        summary="Illustrative analytical screen for chart rendering validation.",
        screens=[{
            "sequence": 1,
            "name": spec.name,
            "screen_type": spec.screen_type,
            "purpose": spec.purpose,
            "components": [component.model_dump()],
            "image_base64": base64.b64encode(screenshot).decode("ascii"),
        }],
    )
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document_pdf:
        assert document_pdf.page_count >= 1
        assert "SCREEN 01" in " ".join(document_pdf[1].get_text().split())
        assert document_pdf[1].get_images()


@pytest.mark.parametrize(
    ("chart_type", "expected_markup"),
    [
        ("pie", 'aria-label="Pie chart"'),
        ("donut", 'aria-label="Donut chart"'),
        ("bar", 'aria-label="Bar chart"'),
        ("column", 'aria-label="Column chart"'),
        ("line", 'aria-label="Line chart"'),
        ("area", 'aria-label="Area chart"'),
        ("stacked_bar", "chart-stack-track"),
        ("stacked_area", 'aria-label="Stacked Area chart"'),
    ],
)
def test_html_renderer_renders_structured_visualizations_and_provenance(chart_type, expected_markup):
    labels = ["Reef station", "Trench station"] if chart_type in {"pie", "donut", "bar", "column"} else [
        "Survey week 1",
        "Survey week 2",
    ]
    datasets = [{
        "name": "Acoustic events",
        "unit": "events",
        "data": [{"label": labels[0], "value": 12}, {"label": labels[1], "value": 8}],
    }]
    if chart_type in {"stacked_bar", "stacked_area"}:
        datasets.append({
            "name": "Signal detections",
            "unit": "events",
            "data": [{"label": labels[0], "value": 7}, {"label": labels[1], "value": 5}],
        })

    spec = ScreenSpecification(
        screen_id="SCREEN-OBSERVATORY-01",
        sequence=1,
        name="Field analysis",
        purpose="Review measured activity across observation sites.",
        screen_type="report",
        components=[ScreenComponent(
            type="visualization",
            title="Generic component heading",
            visualization={
                "type": chart_type,
                "title": "Observation activity",
                "description": "Compares source-defined event counts.",
                "business_purpose": "Help analysts compare survey activity.",
                "data_source": "illustrative",
                "source_reference": "Observation reporting requirement",
                "datasets": datasets,
                "legend_position": "bottom",
                "x_axis_label": "Observation period",
                "y_axis_label": "Events",
                "sample_data": True,
                "note": "Illustrative sample data—not actual results",
                "interpretation": "Compare the displayed counts across the selected categories.",
            },
        )],
    )

    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert expected_markup in document
    assert "Observation activity" in document
    assert "Generic component heading" not in document
    assert labels[0] in document
    assert "12 events" in document
    assert "Illustrative sample data—not actual results" in document
    assert "Observation reporting requirement" in document
    if chart_type not in {"pie", "donut"}:
        assert "Observation period" in document


def test_html_renderer_composes_multiple_charts_and_domain_neutral_kpis():
    components = []
    for chart_type, title, labels in [
        ("bar", "Samples by habitat", ["Tidal pool", "Open water"]),
        ("line", "Readings by cycle", ["Cycle 1", "Cycle 2"]),
    ]:
        components.append(ScreenComponent(
            type="visualization",
            visualization={
                "type": chart_type,
                "title": title,
                "business_purpose": f"Review {title.lower()}.",
                "data_source": "screen_data",
                "datasets": [{
                    "name": "Samples",
                    "unit": "records",
                    "data": [{"label": labels[0], "value": 4}, {"label": labels[1], "value": 9}],
                }],
            },
        ))
    spec = ScreenSpecification(
        screen_id="SCREEN-MULTI-CHART",
        sequence=1,
        name="Observatory overview",
        purpose="Review field observations.",
        screen_type="dashboard",
        header_stats=[{"label": "Recorded sites", "value": "13", "data_source": "screen_data"}],
        components=components,
    )

    document = HtmlScreenRenderer().build_document(spec, DesignContext())

    assert document.count('class="panel chart-panel"') == 2
    assert "Samples by habitat" in document
    assert "Readings by cycle" in document
    assert "Recorded sites" in document
    assert "13" in document


def test_html_renderer_leaves_non_visual_screens_without_chart_markup():
    document = HtmlScreenRenderer().build_document(_spec(), DesignContext())

    assert '<div class="chart-wrap"' not in document
    assert 'aria-label="Column chart"' not in document


def test_html_renderer_formats_structured_units_and_uses_visualization_title():
    component = ScreenComponent(
        type="visualization",
        title="Fallback title",
        visualization={
            "type": "column",
            "title": "Equipment by site",
            "data_source": "brd",
            "datasets": [{
                "name": "Equipment",
                "unit": "units",
                "data": [{"label": "Site North", "value": 15}, {"label": "Site South", "value": 7}],
            }],
        },
    )
    screen = ScreenSpecification(
        screen_id="SCREEN-UNITS",
        name="Equipment report",
        purpose="Compare equipment counts.",
        screen_type="report",
        components=[component],
    )
    document = HtmlScreenRenderer().build_document(screen, DesignContext())

    assert "Equipment by site" in document
    assert "Fallback title" not in document
    assert "15 units" in document
    assert "7 units" in document


def test_column_chart_renders_responsive_svg_in_chromium():
    spec = ScreenSpecification(
        screen_id="SCREEN-COLUMN-CHROMIUM",
        name="Field comparison",
        purpose="Compare observations across sites.",
        screen_type="report",
        components=[ScreenComponent(
            type="visualization",
            visualization={
                "type": "column",
                "title": "Observations by site",
                "data_source": "screen_data",
                "datasets": [{
                    "name": "Observations",
                    "unit": "records",
                    "data": [{"label": "North site", "value": 15}, {"label": "South site", "value": 7}],
                }],
            },
        )],
    )

    screenshot = HtmlScreenRenderer().render(spec, DesignContext())

    with Image.open(io.BytesIO(screenshot)) as image:
        assert image.width == 1600
        assert image.height >= 900
        assert image.getbbox() == (0, 0, image.width, image.height)


@pytest.mark.parametrize(
    "visualization",
    [
        {"type": "pie", "title": "Missing values", "data_source": "screen_data", "datasets": [{"name": "Items", "data": []}]},
        {"type": "column", "title": "Missing point value", "data_source": "screen_data", "datasets": [{"name": "Items", "data": [{"label": "North"}]}]},
    ],
)
def test_html_renderer_rejects_missing_visualization_data(visualization):
    with pytest.raises(ValidationError):
        ScreenComponent(type="visualization", visualization=visualization)


def test_screenshots_with_multiple_and_absent_charts_compile_in_screen_sequence():
    renderer = HtmlScreenRenderer()
    screens = [
        ScreenSpecification(
            screen_id="SCREEN-03",
            sequence=3,
            name="Observation intake",
            purpose="Record a new field observation.",
            screen_type="create_form",
            fields=[ScreenField(label="Observation note")],
            components=[ScreenComponent(
                type="table",
                title="Recent observations",
                columns=["Site", "Status"],
                rows=[{"Site": "North station", "Status": "Recorded"}],
            )],
        ),
        ScreenSpecification(
            screen_id="SCREEN-02",
            sequence=2,
            name="Habitat distribution",
            purpose="Review the illustrative distribution by habitat.",
            screen_type="report",
            components=[ScreenComponent(
                type="visualization",
                visualization={
                    "type": "donut",
                    "title": "Observations by habitat",
                    "business_purpose": "Review habitat representation.",
                    "data_source": "illustrative",
                    "source_reference": "BRD requests habitat distribution; no records supplied",
                    "datasets": [{
                        "name": "Observations",
                        "unit": "records",
                        "data": [{"label": "Tidal pool", "value": 8}, {"label": "Open water", "value": 4}],
                    }],
                    "sample_data": True,
                    "note": "Illustrative sample data—not actual results",
                    "legend_position": "right",
                },
            )],
        ),
        ScreenSpecification(
            screen_id="SCREEN-01",
            sequence=1,
            name="Field analytics",
            purpose="Compare source-reported readings and categories.",
            screen_type="dashboard",
            header_stats=[{"label": "Recorded sites", "value": "3", "data_source": "brd"}],
            components=[
                ScreenComponent(
                    type="visualization",
                    visualization={
                        "type": "bar",
                        "title": "Readings by site",
                        "business_purpose": "Compare BRD-reported readings.",
                        "data_source": "brd",
                        "source_reference": "BRD section 2.1",
                        "datasets": [{
                            "name": "Readings",
                            "unit": "samples",
                            "data": [{"label": "North station", "value": 18}, {"label": "South station", "value": 11}],
                        }],
                        "x_axis_label": "Site",
                        "y_axis_label": "Samples",
                    },
                ),
                ScreenComponent(
                    type="visualization",
                    visualization={
                        "type": "line",
                        "title": "Readings by survey period",
                        "business_purpose": "Review source-reported readings over periods.",
                        "data_source": "screen_data",
                        "datasets": [{
                            "name": "Readings",
                            "unit": "samples",
                            "data": [{"label": "Survey 1", "value": 9}, {"label": "Survey 2", "value": 14}],
                        }],
                        "x_axis_label": "Survey period",
                        "y_axis_label": "Samples",
                    },
                ),
            ],
        ),
    ]

    screenshots = {
        screen.sequence: renderer.render(screen, DesignContext())
        for screen in screens
    }
    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Field Observatory",
        project_name="Survey Operations",
        brd_name="observatory-requirements.pdf",
        summary="Review field observations, site readings, and habitat distribution.",
        screens=[
            {
                "sequence": screen.sequence,
                "name": screen.name,
                "screen_type": screen.screen_type,
                "purpose": screen.purpose,
                "image_base64": base64.b64encode(screenshots[screen.sequence]).decode("ascii"),
            }
            for screen in screens
        ],
    )

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        mockup_pages = [
            page for page in document
            if "UI MOCKUP" in " ".join(page.get_text().split())
        ]
        assert len(mockup_pages) == 3
        mockup_headers = [" ".join(page.get_text().split()) for page in mockup_pages]
        assert ["SCREEN 01" in header for header in mockup_headers] == [True, False, False]
        assert ["SCREEN 02" in header for header in mockup_headers] == [False, True, False]
        assert ["SCREEN 03" in header for header in mockup_headers] == [False, False, True]

        for sequence, page in enumerate(mockup_pages, start=1):
            image_refs = page.get_images(full=True)
            assert image_refs, f"Screen {sequence} screenshot was not embedded in its PDF page."
            extracted = document.extract_image(image_refs[0][0])
            with Image.open(io.BytesIO(screenshots[sequence])) as expected_image:
                with Image.open(io.BytesIO(extracted["image"])) as embedded_image:
                    assert embedded_image.size == expected_image.size
                    assert ImageChops.difference(
                        embedded_image.convert("RGB"),
                        expected_image.convert("RGB"),
                    ).getbbox() is None

    no_chart_html = renderer.build_document(screens[0], DesignContext())
    assert '<div class="chart-wrap"' not in no_chart_html
    assert "Observation note" in no_chart_html
    assert "Recent observations" in no_chart_html


@pytest.mark.parametrize(
    ("brd", "application_name", "application_type", "visualizations", "illustrative"),
    [
        (
            "Healthcare clinic reporting requires appointment outcomes and completed visits by day. "
            "The BRD reports 18 completed appointments and 6 rescheduled appointments; "
            "completed visits were 8 on Monday and 10 on Tuesday.",
            "Clinic Visit Operations",
            "Healthcare appointment management",
            [
                ("donut", "Appointment outcomes", "Appointments", [("Completed", 18), ("Rescheduled", 6)]),
                ("line", "Completed visits by day", "Completed visits", [("Monday", 8), ("Tuesday", 10)]),
            ],
            False,
        ),
        (
            "E-commerce order reporting requires product-category comparisons and daily order volume. "
            "The BRD lists 12 book orders and 8 tool orders; daily orders were 9 on Monday and 11 on Tuesday.",
            "Commerce Order Insights",
            "E-commerce order analytics",
            [
                ("bar", "Orders by category", "Orders", [("Books", 12), ("Tools", 8)]),
                ("line", "Orders by day", "Orders", [("Monday", 9), ("Tuesday", 11)]),
            ],
            False,
        ),
        (
            "The HR recruitment dashboard must show candidate distribution across Applied, Interview, and Offer stages "
            "and application volume by month. No historical records are supplied; clearly labeled illustrative data "
            "may be used for the requested planning visualizations.",
            "Talent Pipeline",
            "Recruitment management",
            [
                ("donut", "Candidates by stage", "Candidates", [("Applied", 24), ("Interview", 9), ("Offer", 3)]),
                ("line", "Applications by month", "Applications", [("January", 18), ("February", 21)]),
            ],
            True,
        ),
        (
            "Logistics performance reporting requires delivery status distribution and parcel volume by week. "
            "The BRD records 42 on-time deliveries and 8 delayed deliveries; parcel shipments were 20 in week 1 "
            "and 30 in week 2.",
            "Parcel Flow Monitor",
            "Logistics delivery operations",
            [
                ("donut", "Delivery status", "Deliveries", [("On time", 42), ("Delayed", 8)]),
                ("area", "Shipments by week", "Shipments", [("Week 1", 20), ("Week 2", 30)]),
            ],
            False,
        ),
    ],
)
def test_cross_domain_dynamic_visualization_to_pdf(
    monkeypatch,
    tmp_path,
    brd,
    application_name,
    application_type,
    visualizations,
    illustrative,
):
    plan_data = {
        "application_name": application_name,
        "application_summary": f"BRD-based {application_type} reporting.",
        "design_context": {
            "application_type": application_type,
            "brand_name": application_name,
        },
        "screens": [{
            "screen_id": "SCREEN-ANALYTICS",
            "sequence": 1,
            "name": f"{application_type} analysis",
            "purpose": f"Review BRD-required {application_type} measures.",
            "screen_type": "report",
            "components": [
                {
                    "type": "visualization",
                    "visualization": {
                        "screen_id": "SCREEN-ANALYTICS",
                        "business_purpose": f"Analyze the {title.lower()} requirement.",
                        "type": chart_type,
                        "title": title,
                        "description": f"BRD-grounded {title.lower()} chart.",
                        "data_source": "illustrative" if illustrative else "brd",
                        "source_reference": "BRD reporting requirement",
                        "datasets": [{
                            "name": dataset_name,
                            "unit": "records",
                            "data": [{"label": label, "value": value} for label, value in points],
                        }],
                        "legend_position": "bottom",
                        "x_axis_label": "Category or period",
                        "y_axis_label": "Records",
                        "sample_data": illustrative,
                        "note": "Illustrative sample data—not actual results" if illustrative else "",
                        "interpretation": f"Compare {dataset_name.lower()} across the stated categories.",
                    },
                }
                for chart_type, title, dataset_name, points in visualizations
            ],
        }],
    }

    class FakeGemini:
        def generate_dict(self, prompt, response_schema=None, require_object=False):
            assert brd in prompt
            assert "Never assume a particular industry" in prompt
            assert "Do not fabricate values for data_source" in prompt
            assert "banking" not in prompt.casefold()
            return plan_data

    planner = ScreenPlanService()
    planner.gemini = FakeGemini()
    plan = planner.generate_plan(brd, application_name)
    screen = plan.screens[0]
    assert plan.application_name == application_name
    assert plan.design_context.application_type == application_type
    assert len(screen.components) == len(visualizations)
    assert [component.visualization.type for component in screen.components] == [
        chart[0] for chart in visualizations
    ]

    for component, (_, title, dataset_name, expected_points) in zip(screen.components, visualizations):
        specification = component.visualization
        assert specification.title == title
        assert specification.datasets[0].name == dataset_name
        assert [(point.label, point.value) for point in specification.datasets[0].data] == expected_points
        assert specification.data_source == ("illustrative" if illustrative else "brd")
        assert specification.sample_data is illustrative
        if illustrative:
            assert "illustrative" in specification.note.casefold()
        else:
            assert "bank" not in " ".join(
                [specification.title, specification.business_purpose, specification.interpretation]
            ).casefold()

    monkeypatch.setenv("IMAGE_GENERATOR_PROVIDER", "stability")
    renderer = HtmlScreenRenderer()
    image_service = ImageGenerationService(renderer)
    image_service.api_key = "mock-stability-key"
    image_service.asset_dir = tmp_path
    mock_artwork = _png_bytes(320, 180)
    artwork_calls = []

    def fake_stability_asset(specification, design):
        artwork_calls.append(specification.screen_id)
        return mock_artwork

    monkeypatch.setattr(image_service, "_get_stability_asset", fake_stability_asset)
    screenshot = image_service.generate_screen_image(screen, plan.design_context)
    assert artwork_calls == ["SCREEN-ANALYTICS"]

    document_html = renderer.build_document(screen, plan.design_context, mock_artwork)
    for _, title, dataset_name, expected_points in visualizations:
        assert title in document_html
        assert dataset_name in document_html
        for label, value in expected_points:
            assert label in document_html
            assert f"{value} records" in document_html
    if illustrative:
        assert "Illustrative sample data—not actual results" in document_html

    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name=plan.application_name,
        project_name=None,
        brd_name="domain-requirements.pdf",
        summary=plan.application_summary,
        screens=[{
            "sequence": screen.sequence,
            "name": screen.name,
            "screen_type": screen.screen_type,
            "purpose": screen.purpose,
            "image_base64": base64.b64encode(screenshot).decode("ascii"),
        }],
    )
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        mockup_pages = [
            page for page in pdf
            if "UI MOCKUP" in " ".join(page.get_text().split())
        ]
        assert len(mockup_pages) == 1
        assert "SCREEN 01" in " ".join(mockup_pages[0].get_text().split())
        images = mockup_pages[0].get_images(full=True)
        assert images
        embedded = pdf.extract_image(images[0][0])
        with Image.open(io.BytesIO(screenshot)) as expected_image:
            with Image.open(io.BytesIO(embedded["image"])) as embedded_image:
                assert embedded_image.size == expected_image.size
                assert ImageChops.difference(
                    embedded_image.convert("RGB"),
                    expected_image.convert("RGB"),
                ).getbbox() is None


def test_cross_domain_planning_omits_visualizations_without_numeric_reporting_needs():
    brd = (
        "The internal policy review application lets editors draft policy language, "
        "request review, and publish approved text. The BRD specifies no numeric reports, "
        "measurements, comparisons, or trends."
    )
    plan_data = {
        "application_name": "Policy Editor",
        "application_summary": "Draft and review policy language.",
        "screens": [{
            "screen_id": "SCREEN-EDITOR",
            "sequence": 1,
            "name": "Policy draft",
            "purpose": "Edit and submit policy text for review.",
            "screen_type": "edit_form",
            "components": [{"type": "form", "title": "Policy content"}],
        }],
    }

    class FakeGemini:
        def generate_dict(self, prompt, response_schema=None, require_object=False):
            assert brd in prompt
            assert "If meaningful numerical data is unavailable, omit the chart" in prompt
            return plan_data

    planner = ScreenPlanService()
    planner.gemini = FakeGemini()
    plan = planner.generate_plan(brd, "Policy Editor")

    assert plan.screens[0].components[0].visualization is None
    assert plan.screens[0].components[0].chart_type is None


def test_screen_rejects_duplicate_visualizations():
    component = {
        "type": "visualization",
        "visualization": {
            "type": "bar",
            "title": "Count by location",
            "data_source": "screen_data",
            "datasets": [{"name": "Samples", "data": [{"label": "North", "value": 3}, {"label": "South", "value": 5}]}],
        },
    }

    with pytest.raises(ValidationError, match="duplicate visualizations"):
        ScreenSpecification(
            screen_id="SCREEN-DUPLICATES",
            name="Counts",
            purpose="Compare counts.",
            screen_type="report",
            components=[component, {**component, "visualization": {**component["visualization"], "title": "Repeated counts"}}],
        )


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
        assert image.width == 1600
        assert image.height >= 900
        assert image.getbbox() == (0, 0, image.width, image.height)

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


def test_pdf_metadata_reports_the_configured_html_and_visual_asset_providers(monkeypatch):
    monkeypatch.setattr(settings, "image_generator_provider", "stability")
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
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")

    assert "Chromium HTML/CSS renderer" in document.metadata["creator"]
    assert "Stability AI decorative assets" in document.metadata["subject"]
    assert "STABILITY_API_KEY" not in str(document.metadata)
    document.close()


@pytest.mark.skipif(
    os.getenv("RUN_STABILITY_INTEGRATION_TEST") != "1" or not settings.stability_api_key,
    reason="Set RUN_STABILITY_INTEGRATION_TEST=1 and STABILITY_API_KEY for a live Stability API check.",
)
def test_live_stability_api_generates_and_stores_a_decorative_asset(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGE_GENERATOR_PROVIDER", "stability")
    service = ImageGenerationService(CapturingHtmlRenderer())
    service.asset_dir = tmp_path

    image = service.generate_screen_image(_spec(), DesignContext())

    assert Image.open(io.BytesIO(image)).format == "PNG"
    assert len(list(tmp_path.glob("form-*.png"))) == 1
