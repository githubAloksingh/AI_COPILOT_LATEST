import base64
from app.api.schemas import DesignContext, ScreenSpecification
from app.services.image_generation_service import image_generation_service
from app.services.wireframe_service import wireframe_service
from app.services.pdf_compilation_service import pdf_compilation_service


def test_pdf_compilation_three_pages_per_screen():
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
    # Expected: 1 cover page + 0 overflow TOC (<= 14 screens) + (3 pages * 2 screens) = 1 + 6 = 7 pages
    assert pdf_compilation_service.count_pages(pdf_bytes) == 7
