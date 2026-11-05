import base64
import io
from importlib import import_module
import os

import httpx
import pytest
import pymupdf
from PIL import Image

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
        (402, "insufficient credits", 402),
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
