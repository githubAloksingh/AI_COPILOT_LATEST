import base64
import io
import pytest
from PIL import Image
import pymupdf

from app.api.schemas import (
    ChartDataPoint,
    ChartSeries,
    ChartSpecification,
    DesignContext,
    ScreenComponent,
    ScreenSpecification,
    ScreenPlan,
)
from app.services.html_screen_renderer import HtmlScreenRenderer
from app.services.pdf_compilation_service import pdf_compilation_service


def test_chart_spec_bidirectional_synchronization():
    # 1. Provide chart_spec, verify chart_type and chart_data are derived automatically
    spec1 = ScreenSpecification(
        screen_id="SCREEN-001",
        sequence=1,
        name="Supply Chain Throughput",
        purpose="Monitor daily freight throughput by transport mode.",
        screen_type="dashboard",
        components=[
            ScreenComponent(
                type="chart",
                title="Freight Volume by Mode",
                chart_spec=ChartSpecification(
                    chart_type="bar",
                    title="Freight Volume by Mode",
                    labels=["Air", "Ocean", "Rail", "Truck"],
                    values=[1200, 8500, 4300, 9600],
                    legends=["Volume (Tons)"],
                    dimensions={"width": "100%", "height": 380},
                    placement="main",
                ),
                chart_data_source="brd",
            )
        ],
    )
    comp1 = spec1.components[0]
    assert comp1.chart_type == "bar"
    assert len(comp1.chart_data) == 4
    assert comp1.chart_data[0].label == "Air"
    assert comp1.chart_data[0].value == 1200
    assert comp1.chart_spec.placement == "main"

    # 2. Provide chart_type and chart_data, verify chart_spec is constructed automatically
    spec2 = ScreenSpecification(
        screen_id="SCREEN-002",
        sequence=2,
        name="Clinical Trial Progression",
        purpose="Track patient cohorts across trial phases.",
        screen_type="analytics",
        components=[
            ScreenComponent(
                type="chart",
                title="Patients by Phase",
                chart_type="donut",
                chart_data=[
                    ChartDataPoint(label="Phase I", value=25),
                    ChartDataPoint(label="Phase II", value=60),
                    ChartDataPoint(label="Phase III", value=140),
                ],
                chart_data_source="brd",
            )
        ],
    )
    comp2 = spec2.components[0]
    assert comp2.chart_spec is not None
    assert comp2.chart_spec.chart_type == "donut"
    assert comp2.chart_spec.labels == ["Phase I", "Phase II", "Phase III"]
    assert comp2.chart_spec.values == [25, 60, 140]


@pytest.mark.parametrize(
    "chart_type,labels,values",
    [
        ("bar", ["North", "South", "East", "West"], [420.0, 310.0, 590.0, 280.0]),
        ("line", ["Jan", "Feb", "Mar", "Apr", "May"], [15.0, 22.0, 38.0, 45.0, 52.0]),
        ("pie", ["Renewable", "Natural Gas", "Nuclear"], [35.0, 45.0, 20.0]),
        ("donut", ["Compliant", "Under Review", "Non-Compliant"], [82.0, 12.0, 6.0]),
        ("area", ["Week 1", "Week 2", "Week 3", "Week 4"], [100.0, 250.0, 480.0, 720.0]),
        ("radar", ["Speed", "Reliability", "Cost", "Safety", "Efficiency"], [85.0, 92.0, 78.0, 95.0, 88.0]),
        ("gauge", ["SLA Fulfillment"], [98.5]),
    ],
)
def test_echarts_html_document_generation_for_dynamic_chart_types(chart_type, labels, values):
    spec = ScreenSpecification(
        screen_id="SCREEN-DYNAMIC-01",
        sequence=1,
        name="Performance Overview",
        purpose="Industry-agnostic quantitative performance view.",
        screen_type="dashboard",
        components=[
            ScreenComponent(
                type="chart",
                title="Dynamic Metric Tracking",
                chart_spec=ChartSpecification(
                    chart_type=chart_type,
                    title="Dynamic Metric Tracking",
                    labels=labels,
                    values=values,
                    legends=["Performance Metric"],
                    dimensions={"width": "100%", "height": 340},
                    placement="full_width",
                ),
                chart_data=[ChartDataPoint(label=l, value=v) for l, v in zip(labels, values)],
                chart_data_source="brd",
            )
        ],
    )
    design = DesignContext(
        application_type="Industrial Logistics Management",
        primary_color="#0F766E",
        secondary_color="#0369A1",
        accent_color="#D97706",
    )
    renderer = HtmlScreenRenderer()
    document = renderer.build_document(spec, design)

    assert "echarts-chart-box" in document
    assert "echarts.init" in document
    assert "window.__echarts_ready = true" in document
    assert "#0F766E" in document or "#0f766e" in document.lower()
    assert 'class="panel chart-panel single-chart"' in document


def test_playwright_renders_echarts_to_mockup_and_consolidated_pdf():
    spec = ScreenSpecification(
        screen_id="SCREEN-ENERGY-01",
        sequence=1,
        name="Grid Load & Generation",
        purpose="Real-time monitoring of energy production across renewable sources.",
        screen_type="dashboard",
        user_role="Grid Controller",
        components=[
            ScreenComponent(
                type="chart",
                title="Generation by Source",
                chart_spec=ChartSpecification(
                    chart_type="bar",
                    title="Generation by Source",
                    labels=["Solar", "Wind", "Hydro", "Biomass"],
                    values=[450.0, 820.0, 310.0, 110.0],
                    legends=["Megawatts (MW)"],
                    dimensions={"width": "100%", "height": 340},
                    placement="main",
                ),
                chart_value_suffix=" MW",
                chart_data_source="brd",
            )
        ],
    )
    design = DesignContext(
        application_type="Smart Energy Grid Management",
        brand_name="EcoGrid",
        primary_color="#059669",
        secondary_color="#0284C7",
    )
    renderer = HtmlScreenRenderer()
    png_bytes = renderer.render(spec, design)

    # Verify Playwright captured a full mockup PNG with content
    with Image.open(io.BytesIO(png_bytes)) as img:
        assert img.format == "PNG"
        assert img.width == 1600
        assert img.height >= 900

    # Compile into consolidated PDF and verify inclusion
    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="EcoGrid",
        project_name="Clean Power",
        brd_name="Smart Grid Phase 1 BRD",
        summary="Comprehensive grid operations interface.",
        screens=[
            {
                "sequence": 1,
                "name": spec.name,
                "screen_type": spec.screen_type,
                "purpose": spec.purpose,
                "user_role": spec.user_role,
                "components": [c.model_dump() for c in spec.components],
                "image_base64": base64.b64encode(png_bytes).decode("ascii"),
            }
        ],
    )

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        assert doc.page_count >= 2
        # Check that screen mockup image is embedded in the PDF
        images = doc[1].get_images()
        assert len(images) > 0
        pdf_text = " ".join("\n".join(page.get_text() for page in doc).split())
        assert "Chart: bar" in pdf_text
        assert "Solar: 450 MW" in pdf_text
        assert "Wind: 820 MW" in pdf_text


def test_illustrative_chart_data_handling_and_validation():
    # When numbers are absent from BRD, illustrative sample data must be labeled
    spec = ScreenSpecification(
        screen_id="SCREEN-HEALTHCARE-01",
        sequence=1,
        name="Patient Triage Distribution",
        purpose="Examine triage acuity levels across emergency admissions.",
        screen_type="report",
        components=[
            ScreenComponent(
                type="chart",
                title="Acuity Breakdown",
                chart_type="pie",
                chart_data=[
                    ChartDataPoint(label="Resuscitation", value=5),
                    ChartDataPoint(label="Emergent", value=22),
                    ChartDataPoint(label="Urgent", value=48),
                ],
                chart_data_source="illustrative",
                chart_note="Illustrative data based on typical hospital triage distribution.",
            )
        ],
    )
    renderer = HtmlScreenRenderer()
    document = renderer.build_document(spec, DesignContext())
    assert "Illustrative data" in document

    # Verify that omitting the illustrative note raises validation error
    with pytest.raises(ValueError, match="labeled in chart_note"):
        ScreenComponent(
            type="chart",
            chart_type="bar",
            chart_data=[ChartDataPoint(label="A", value=10)],
            chart_data_source="illustrative",
            chart_note="",
        )
