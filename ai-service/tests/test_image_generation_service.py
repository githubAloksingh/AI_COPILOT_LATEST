import pymupdf

from app.api.schemas import (
    DesignContext,
    HeaderStat,
    ScreenAction,
    ScreenComponent,
    ScreenField,
    ScreenSpecification,
)
from app.services.image_generation_service import ImageGenerationService


def _screen(screen_type, name, purpose, **kwargs):
    return ScreenSpecification(
        screen_type=screen_type,
        name=name,
        purpose=purpose,
        **kwargs,
    )


def _render_body_text(spec):
    document = pymupdf.open()
    page = document.new_page(width=1600, height=920)
    ImageGenerationService()._render_screen_body(
        page, spec, DesignContext(), 40, 100, 1520, 880
    )
    text = page.get_text()
    document.close()
    return text


def _render_body_page(spec):
    document = pymupdf.open()
    page = document.new_page(width=1600, height=920)
    ImageGenerationService()._render_screen_body(
        page, spec, DesignContext(), 40, 100, 1520, 880
    )
    return document, page


def test_screen_intent_selects_distinct_layout_archetypes():
    service = ImageGenerationService()
    cases = [
        (_screen("dashboard", "Operations overview", "Monitor activity"), "overview"),
        (_screen("work_queue", "Open requests", "Triage incoming work"), "work_queue"),
        (_screen("create_form", "Create request", "Enter a new request"), "form"),
        (_screen("approval", "Approval decision", "Approve a submitted request"), "approval"),
        (_screen("detail_view", "Case detail", "Inspect the case record"), "detail"),
        (_screen("document_viewer", "Document review", "Review attached documents"), "document_review"),
        (_screen("report", "Monthly analytics", "Analyze performance"), "report"),
        (_screen("workflow_stepper", "Setup workflow", "Complete guided setup"), "workflow"),
    ]

    assert [service._classify_layout(spec) for spec, _ in cases] == [
        expected for _, expected in cases
    ]


def test_explicit_supplier_create_form_stays_a_form_without_workflow_strip():
    spec = _screen(
        "create_form",
        "Create supplier request",
        "Start supplier onboarding and capture the initial supplier request.",
        fields=[ScreenField(label="Supplier name", value="Northwind")],
        components=[ScreenComponent(type="workflow_stepper", steps=[])],
    )
    service = ImageGenerationService()
    assert service._classify_layout(spec) == "form"

    text = _render_body_text(spec)
    assert "Supplier name" in text
    assert "WORKFLOW" not in text


def test_approval_document_detail_and_report_have_task_specific_compositions():
    examples = [
        (
            _screen(
                "approval",
                "Credit decision",
                "Review the submitted request and decide whether to approve it.",
                fields=[ScreenField(label="Requested limit", value="$75,000")],
                actions=[ScreenAction(label="Approve", type="primary")],
                business_rules=["Requests above the threshold require a second approver."],
            ),
            "DECISION",
        ),
        (
            _screen(
                "document_viewer",
                "Evidence review",
                "Inspect the submitted evidence against the requirements.",
                components=[ScreenComponent(type="document", title="Supporting evidence")],
                notifications=["One attachment requires review."],
            ),
            "REVIEW PANEL",
        ),
        (
            _screen(
                "detail_view",
                "Request record",
                "Inspect the request record and its current state.",
                fields=[ScreenField(label="Request ID", value="REQ-18")],
            ),
            "RECORD SUMMARY",
        ),
        (
            _screen(
                "report",
                "Service performance",
                "Analyze completed requests by processing time.",
                header_stats=[HeaderStat(label="Median duration", value="4.2 days")],
            ),
            "PERFORMANCE INDICATORS",
        ),
    ]

    rendered = [_render_body_text(spec) for spec, _ in examples]
    for text, (_, marker) in zip(rendered, examples):
        assert marker in text
    assert len(set(rendered)) == len(rendered)


def test_report_and_document_review_render_supplied_component_content():
    report = _screen(
        "report",
        "Supplier status report",
        "Review supplier onboarding status by region.",
        components=[
            ScreenComponent(
                type="table",
                columns=["Supplier", "Region", "Status"],
                rows=[{"Supplier": "Northwind", "Region": "West", "Status": "Pending"}],
            )
        ],
    )
    document = _screen(
        "document_viewer",
        "Supplier evidence",
        "Review the supplier's compliance evidence.",
        components=[
            ScreenComponent(
                type="document",
                title="Tax certificate",
                description="Certificate issued by the regional authority.",
                fields=[ScreenField(label="Certificate number", value="TX-420")],
            )
        ],
        data_sources=["Supplier attachments"],
    )

    report_text = _render_body_text(report)
    document_text = _render_body_text(document)
    assert all(value in report_text for value in ("Northwind", "West", "Pending"))
    assert all(value in document_text for value in ("Tax certificate", "TX-420"))


def test_missing_report_and_document_content_use_explicit_empty_states():
    report = _screen("report", "Monthly report", "Review monthly performance.")
    document = _screen("document_viewer", "Evidence review", "Inspect evidence.")

    assert "Report data not supplied" in _render_body_text(report)
    assert "Document preview unavailable" in _render_body_text(document)


def test_navigation_selects_exactly_one_item_for_repeated_screen_types():
    service = ImageGenerationService()
    nav_items = [
        ("Dashboard", "dashboard"),
        ("Search & Tracker", "detail_view"),
        ("Requests & Details", "detail_view"),
        ("Approval Queue", "approval"),
    ]
    spec = _screen("detail_view", "Supplier record", "Inspect supplier details.")

    active_index = service._active_navigation_index(spec, nav_items)
    assert active_index is not None
    assert sum(index == active_index for index in range(len(nav_items))) == 1
    assert nav_items[active_index][0] == "Requests & Details"


def test_dynamic_navigation_label_is_not_cut_mid_word():
    label = ImageGenerationService()._fit_navigation_label("Create supplier request", 175)
    assert label == "Create supplier request"


def test_form_action_is_rendered_once_in_its_task_panel():
    spec = _screen(
        "create_form",
        "Create supplier request",
        "Capture supplier information.",
        fields=[ScreenField(label="Supplier name", value="Northwind")],
        actions=[ScreenAction(label="Create supplier", type="primary")],
    )
    document, page = _render_body_page(spec)
    try:
        assert page.get_text().splitlines().count("Create supplier") == 1
    finally:
        document.close()
    assert ImageGenerationService()._header_actions_for_screen(spec, "form") == []


def test_absent_actions_stay_absent_and_report_export_has_one_owner():
    service = ImageGenerationService()
    empty_report = _screen("report", "Monthly report", "Review monthly performance.")
    exported_report = _screen(
        "report",
        "Supplier status report",
        "Review supplier status by region.",
        actions=[ScreenAction(label="Export report", type="secondary")],
    )

    assert service._header_actions_for_screen(empty_report, "report") == []
    assert service._header_actions_for_screen(exported_report, "report") == []
    assert service._header_actions_for_screen(exported_report, "overview") == exported_report.actions


def test_report_distribution_is_derived_only_from_supplied_rows():
    service = ImageGenerationService()
    rows = [
        {"Supplier": "Northwind", "Region": "West", "Status": "Pending"},
        {"Supplier": "Contoso", "Region": "West", "Status": "Pending"},
        {"Supplier": "Fabrikam", "Region": "East", "Status": "Approved"},
    ]

    assert service._report_distribution(["Supplier", "Region", "Status"], rows) == (
        "Status",
        [("Pending", 2), ("Approved", 1)],
    )
    assert service._report_distribution(["Supplier", "Region", "Status"], []) == []


def test_report_renders_data_derived_distribution_and_compact_table():
    report = _screen(
        "report",
        "Supplier status report",
        "Review supplier onboarding status by region.",
        components=[
            ScreenComponent(
                type="table",
                columns=["Supplier", "Region", "Status"],
                rows=[
                    {"Supplier": "Northwind", "Region": "West", "Status": "Pending"},
                    {"Supplier": "Contoso", "Region": "West", "Status": "Pending"},
                ],
            )
        ],
    )
    text = _render_body_text(report)
    assert "RECORDS BY STATUS" in text
    assert "Pending" in text
    assert "Northwind" in text


def test_full_renderer_returns_a_valid_png_for_each_task_structure():
    service = ImageGenerationService()
    spec = _screen(
        "workflow_stepper",
        "Supplier onboarding",
        "Collect the supplier's compliance details through the required stages.",
        components=[
            ScreenComponent(
                type="workflow_stepper",
                steps=["Business details", "Documents", "Review"],
                fields=[ScreenField(label="Supplier name", value="Northwind")],
            )
        ],
        actions=[ScreenAction(label="Continue", type="primary")],
    )

    image_bytes = service._render_enterprise_mockup(spec, DesignContext())
    image = pymupdf.open(stream=image_bytes, filetype="png")
    assert image.page_count == 1
    assert image[0].rect.width > 0
    assert image[0].rect.height > 0
    image.close()
