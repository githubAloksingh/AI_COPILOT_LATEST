import io
from PIL import Image
from app.api.schemas import (
    DesignContext,
    HeaderStat,
    ScreenAction,
    ScreenComponent,
    ScreenField,
    ScreenSpecification,
    ScreenTable,
)
from app.services.wireframe_service import wireframe_service


def test_wireframe_render_overview():
    spec = ScreenSpecification(
        screen_id="SCREEN-001",
        sequence=1,
        name="Portfolio Dashboard",
        purpose="Executive overview of portfolio health, active loans, and performance metrics.",
        screen_type="dashboard",
        user_role="Portfolio Manager",
        header_stats=[
            HeaderStat(label="Total Applications", value="1,842"),
            HeaderStat(label="Pending Review", value="64"),
        ],
        tables=[
            ScreenTable(
                title="Recent Loan Applications",
                columns=["App ID", "Borrower", "Amount", "Status", "Date"],
                rows=[{"App ID": "APP-1001", "Borrower": "Acme Corp", "Amount": "$500,000", "Status": "Underwriting"}],
            )
        ],
        actions=[ScreenAction(label="New Application", type="primary")],
    )
    png_bytes = wireframe_service.render_wireframe(spec, DesignContext())
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 10000

    with Image.open(io.BytesIO(png_bytes)) as img:
        assert img.format == "PNG"
        assert img.width >= 1024
        assert img.height >= 576


def test_wireframe_render_form():
    spec = ScreenSpecification(
        screen_id="SCREEN-002",
        sequence=2,
        name="Loan Application Form",
        purpose="Capture applicant personal details, financial parameters, and attached documents.",
        screen_type="create_form",
        user_role="Loan Officer",
        fields=[
            ScreenField(label="Applicant Name", type="text", required=True),
            ScreenField(label="Loan Amount", type="number", required=True),
            ScreenField(label="Term Months", type="select", required=True),
        ],
        actions=[
            ScreenAction(label="Submit Application", type="primary"),
            ScreenAction(label="Save Draft", type="secondary"),
        ],
        business_rules=["Applicant must be >= 18 years old", "Loan amount cannot exceed $5M"],
    )
    png_bytes = wireframe_service.render_wireframe(spec, DesignContext())
    assert isinstance(png_bytes, bytes)

    with Image.open(io.BytesIO(png_bytes)) as img:
        assert img.format == "PNG"
        assert img.width == 1920 or img.width >= 1024
