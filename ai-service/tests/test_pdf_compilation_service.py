import base64
import io
import pymupdf
from PIL import Image

from app.api.schemas import DesignContext, ScreenSpecification
from app.api.schemas import ScreenField, ScreenAction
from app.services.html_screen_renderer import HtmlScreenRenderer
from app.services.image_generation_service import image_generation_service
from app.services.wireframe_service import wireframe_service
from app.services.pdf_compilation_service import pdf_compilation_service


def test_pdf_compilation_mockup_and_explanation_per_screen():
    spec1 = ScreenSpecification(
        screen_id="SCREEN-001",
        sequence=1,
        name="Dashboard Overview",
        purpose="Operational monitoring dashboard with KPI metrics and recent cases.",
        screen_type="dashboard",
        user_role="Operations Analyst",
    )
    spec2 = ScreenSpecification(
        screen_id="SCREEN-002",
        sequence=2,
        name="Transaction Form",
        purpose="Submit new transaction details for processing and validation.",
        screen_type="create_form",
        user_role="Finance Specialist",
    )

    design = DesignContext()
    img1 = image_generation_service.generate_screen_image(spec1, design)
    wf1 = wireframe_service.render_wireframe(spec1, design)

    img2 = image_generation_service.generate_screen_image(spec2, design)
    wf2 = wireframe_service.render_wireframe(spec2, design)

    screens = [
        {
            "sequence": 1,
            "name": spec1.name,
            "screen_type": spec1.screen_type,
            "purpose": spec1.purpose,
            "user_role": spec1.user_role,
            "image_base64": base64.b64encode(img1).decode("utf-8"),
            "wireframe_base64": base64.b64encode(wf1).decode("utf-8"),
            "explanation": {
                "purpose_summary": "Core operational monitoring interface.",
                "sections": [{"title": "KPI Metrics", "fields": [{"name": "Volume", "type": "number", "required": False}]}],
                "actions": [{"label": "Refresh", "type": "secondary", "outcome": "Reloads live metrics"}],
                "validation_rules": ["Metrics refresh rate: 30s"],
                "navigation_flow": "Entry screen upon login.",
                "brd_references": ["BR-01", "Section 2.1"]
            }
        },
        {
            "sequence": 2,
            "name": spec2.name,
            "screen_type": spec2.screen_type,
            "purpose": spec2.purpose,
            "user_role": spec2.user_role,
            "image_base64": base64.b64encode(img2).decode("utf-8"),
            "wireframe_base64": base64.b64encode(wf2).decode("utf-8"),
            "explanation": {
                "purpose_summary": "Transaction capture form.",
                "sections": [{"title": "Parameters", "fields": [{"name": "Amount", "type": "number", "required": True}]}],
                "actions": [{"label": "Submit", "type": "primary", "outcome": "Initiates payment"}],
                "validation_rules": ["Amount > 0"],
                "navigation_flow": "Navigates to Confirmation.",
                "brd_references": ["BR-05"]
            }
        }
    ]

    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Financial Operations Hub",
        project_name="Core Banking Modernization",
        brd_name="BRD_Finance_v2.pdf",
        summary="Automated mock screens and architecture blueprint.",
        screens=screens,
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 20000
    # Expected: 1 cover page + 0 overflow TOC (<= 14 screens) + (2 pages * 2 screens: Mockup + Explanation) = 1 + 4 = 5 pages
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        assert document.page_count >= 5
        assert all(page.rect == pymupdf.Rect(0, 0, 842, 595) for page in document)
        document_text = " ".join(
            "\n".join(page.get_text() for page in document).replace("\u00ad", "-").split()
        ).upper()
        assert "BUSINESS PURPOSE" in document_text
        assert "FIELD INVENTORY" in document_text
        assert "PAGE ACTIONS" in document_text
        assert "BUSINESS RULES" in document_text
        assert "NAVIGATION FLOW" in document_text
        assert "BRD TRACEABILITY" in document_text
        for page_number, page in enumerate(document, start=1):
            page_text = " ".join(page.get_text().replace("\u00ad", "-").split())
            assert f"PAGE {page_number} OF {document.page_count}" in page_text


def _png(width=1600, height=900):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (250, 250, 250)).save(buffer, "PNG")
    return buffer.getvalue()


def test_specification_content_wraps_and_paginates_without_losing_requirements():
    fields = [
        {
            "label": f"Inventory control field {index:02d} with a deliberately long descriptive label",
            "type": "text",
            "required": index % 2 == 0,
            "placeholder": f"Validation instruction for inventory field {index:02d} that must remain visible in the PDF.",
        }
        for index in range(1, 31)
    ]
    rules = [
        f"Inventory rule {index:02d}: record the adjustment reason and preserve the review audit trail."
        for index in range(1, 17)
    ]
    references = [f"REQ-INV-{index:03d}" for index in range(1, 26)]
    screen = {
        "sequence": 1,
        "name": "Stock adjustment review",
        "screen_type": "approval",
        "purpose": "Review proposed inventory changes and capture the outcome. " * 8,
        "fields": fields,
        "actions": [
            {"label": f"Review action {index:02d}", "type": "primary"}
            for index in range(1, 10)
        ],
        "business_rules": rules,
        "related_requirements": references,
        "interaction": {
            "events": [{"label": "Submit for review", "type": "submit"}],
            "navigation_flows": [
                {
                    "from_event": "Submit for review",
                    "to_screen_id": "SCREEN-002",
                    "condition": "review_requested",
                }
            ],
            "data_bindings": [],
            "validation_rules": [],
        },
        "image_base64": base64.b64encode(_png(900, 1600)).decode("ascii"),
    }

    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Inventory Operations",
        project_name="Warehouse Controls",
        brd_name="Inventory Requirements",
        summary="Manage stock adjustments and review workflow.",
        screens=[screen],
    )
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        text = "\n".join(page.get_text() for page in document)
        assert document.page_count > 4
        normalized_text = " ".join(text.replace("\u00ad", "-").split())
        assert "Inventory control field 30 with a deliberately long descriptive label" in normalized_text
        assert "Inventory rule 16: record the adjustment reason" in normalized_text
        assert "REQ-INV-025" in normalized_text
        assert "SCREEN-002" in normalized_text
        assert "triggers Review action processing" not in normalized_text
        for page in document:
            assert page.rect == pymupdf.Rect(0, 0, 842, 595)
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        x0, y0, x1, y1 = span["bbox"]
                        assert x0 >= -0.5
                        assert y0 >= -0.5
                        assert x1 <= page.rect.width + 0.5
                        assert y1 <= page.rect.height + 0.5


def test_pdf_specification_includes_chart_type_provenance_units_and_values():
    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Financial Summary",
        project_name=None,
        brd_name="Cash flow requirements",
        summary="Compare source-defined income and expenses.",
        screens=[
            {
                "sequence": 1,
                "name": "Cash flow",
                "screen_type": "report",
                "purpose": "Compare source-defined income and expenses.",
                "components": [
                    {
                        "type": "chart",
                        "title": "Income and expenses",
                        "chart_type": "bar",
                        "chart_data_source": "brd",
                        "chart_value_prefix": "$",
                        "chart_data": [
                            {"label": "Income", "value": 1250},
                            {"label": "Expenses", "value": -400},
                        ],
                    }
                ],
                "image_base64": base64.b64encode(_png()).decode("ascii"),
            }
        ],
    )

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        pdf_text = " ".join(
            "\n".join(page.get_text() for page in document).replace("\u00ad", "-").split()
        )
        assert "Chart: bar" in pdf_text
        assert "Data source: brd" in pdf_text
        assert "Income: $1250" in pdf_text
        assert "Expenses: -$400" in pdf_text


def test_html_and_pdf_generation_preserve_screens_from_unrelated_brd_domains():
    cases = [
        (
            "Smart Banking Portal",
            "Fund Transfer",
            "Transfer funds between customer-selected accounts.",
            [
                ScreenField(label="Source account", required=True),
                ScreenField(label="Beneficiary", required=True),
                ScreenField(label="Transfer amount", type="number", required=True),
            ],
        ),
        (
            "Workshop Booking",
            "Reserve a Workshop",
            "Select a workshop session and provide attendee details.",
            [
                ScreenField(
                    label="Workshop session",
                    type="select",
                    value="Morning",
                    required=True,
                    options=["Morning", "Afternoon"],
                ),
                ScreenField(label="Attendee name", required=True),
                ScreenField(label="Accessibility needs", type="textarea"),
            ],
        ),
        (
            "Patient Referral Management",
            "Referral Intake",
            "Capture patient referral details for clinical review.",
            [
                ScreenField(label="Patient identifier", required=True),
                ScreenField(label="Referring clinician", required=True),
                ScreenField(label="Referral reason", type="textarea", required=True),
            ],
        ),
    ]
    renderer = HtmlScreenRenderer()
    screens = []
    for sequence, (application, name, purpose, fields) in enumerate(cases, start=1):
        spec = ScreenSpecification(
            screen_id=f"SCREEN-{sequence:03d}",
            sequence=sequence,
            name=name,
            purpose=purpose,
            screen_type="create_form",
            fields=fields,
            actions=[ScreenAction(label="Continue", type="primary")],
            business_rules=["Required information must be entered before continuing."],
            related_requirements=[f"REQ-{sequence:03d}"],
        )
        png = renderer.render(spec, DesignContext(brand_name=application))
        screens.append({
            "sequence": sequence,
            "name": spec.name,
            "purpose": spec.purpose,
            "screen_type": spec.screen_type,
            "fields": [field.model_dump() for field in spec.fields],
            "actions": [action.model_dump() for action in spec.actions],
            "business_rules": spec.business_rules,
            "related_requirements": spec.related_requirements,
            "image_base64": base64.b64encode(png).decode("ascii"),
        })

    pdf_bytes = pdf_compilation_service.compile_pdf(
        application_name="Cross-domain BRD validation",
        project_name=None,
        brd_name="Multiple requirements sources",
        summary="Validate screen layouts across unrelated application domains.",
        screens=screens,
    )
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        pdf_text = " ".join(
            "\n".join(page.get_text() for page in document).replace("\u00ad", "-").split()
        )
        for expected in (
            "Fund Transfer",
            "Source account",
            "Reserve a Workshop",
            "Workshop session",
            "Options: Morning, Afternoon",
            "Value: Morning",
            "Referral Intake",
            "Patient identifier",
            "Required information must be entered before continuing.",
        ):
            assert expected in pdf_text
