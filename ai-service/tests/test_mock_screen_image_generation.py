import hashlib
import io

import pytest
from PIL import Image

from app.api.schemas import (
    DesignContext,
    ScreenAction,
    ScreenComponent,
    ScreenField,
    ScreenSpecification,
    ScreenTable,
)
from app.services.image_generation_service import ImageGenerationService


def _screen(
    screen_id,
    sequence,
    name,
    purpose,
    screen_type,
    *,
    role,
    fields=None,
    tables=None,
    actions=None,
    navigation_items=None,
):
    return ScreenSpecification(
        screen_id=screen_id,
        sequence=sequence,
        name=name,
        purpose=purpose,
        user_role=role,
        screen_type=screen_type,
        fields=fields or [],
        tables=tables or [],
        actions=actions or [],
        navigation_context={
            "active_nav_item": name,
            "navigation_items": navigation_items or [name],
            "breadcrumbs": ["Home", name],
        },
    )


def test_local_renderer_is_the_default_and_does_not_require_gemini_credentials(monkeypatch):
    monkeypatch.delenv("IMAGE_GENERATOR_PROVIDER", raising=False)
    service = ImageGenerationService()
    spec = _screen("KITCHEN-01", 1, "Kitchen tickets", "Prioritize meal preparation.", "work_queue",
                   role="Kitchen lead")

    image_bytes = service.generate_screen_image(spec)

    assert service.provider == "pymupdf"
    assert spec.image_prompt.startswith("PyMuPDF static UI mockup")
    with Image.open(io.BytesIO(image_bytes)) as image:
        assert image.format == "PNG"
        assert image.width >= 1024
        assert image.height >= 576
        image.verify()


def test_screen_brief_contains_domain_fields_tables_actions_and_distinct_layouts():
    service = ImageGenerationService()
    claims = _screen(
        "CLAIM-01",
        1,
        "Claim adjudication workspace",
        "Review diagnosis codes and supporting evidence before deciding a claim.",
        "approval",
        role="Claims adjudicator",
        fields=[ScreenField(label="Diagnosis code")],
        tables=[ScreenTable(columns=["Claim number", "Member", "Evidence status"])],
        actions=[ScreenAction(label="Request missing evidence")],
    )
    kitchen = _screen(
        "ORDER-01",
        1,
        "Kitchen order rail",
        "Prioritize meal tickets by preparation time and dietary restrictions.",
        "work_queue",
        role="Kitchen lead",
        fields=[ScreenField(label="Dietary restriction")],
        tables=[ScreenTable(columns=["Order number", "Pickup time", "Station"])],
        actions=[ScreenAction(label="Mark item ready")],
    )
    design_claims = DesignContext(application_type="Healthcare Claims", brand_name="CareAxis")
    design_kitchen = DesignContext(application_type="Restaurant Operations", brand_name="TableFlow")

    claims_brief = service.build_screen_image_prompt(claims, design_claims)
    kitchen_brief = service.build_screen_image_prompt(kitchen, design_kitchen)

    assert claims_brief != kitchen_brief
    assert all(
        value in claims_brief
        for value in ("diagnosis codes", "Claims adjudicator", "Diagnosis code", "Evidence status", "Request missing evidence", "approval")
    )
    assert all(
        value in kitchen_brief
        for value in ("meal tickets", "Kitchen lead", "Dietary restriction", "Pickup time", "Mark item ready", "work_queue")
    )
    assert "CareAxis" in claims_brief
    assert "TableFlow" in kitchen_brief


def test_different_business_screens_render_different_high_resolution_pngs(monkeypatch):
    monkeypatch.setenv("IMAGE_GENERATOR_PROVIDER", "pymupdf")
    service = ImageGenerationService()
    claims = _screen(
        "CLAIM-01",
        1,
        "Claim review",
        "Review diagnosis evidence and coverage before adjudication.",
        "approval",
        role="Claims examiner",
        fields=[ScreenField(label="Diagnosis code", value="DX-204")],
        actions=[ScreenAction(label="Approve claim"), ScreenAction(label="Escalate for review")],
    )
    kitchen = _screen(
        "ORDER-01",
        1,
        "Expediter rail",
        "Track meal tickets and hold orders until all items are ready.",
        "work_queue",
        role="Kitchen expediter",
        tables=[
            ScreenTable(
                columns=["Order number", "Table", "Allergy warning", "Elapsed time"],
                rows=[{"Order number": "K-104", "Table": "12", "Allergy warning": "Peanut", "Elapsed time": "8 min"}],
            )
        ],
        navigation_items=["Expediter rail", "Shift report"],
    )
    design = DesignContext(navigation_pattern="sidebar_and_header")

    claims_png = service.generate_screen_image(claims, design)
    kitchen_png = service.generate_screen_image(kitchen, design)

    for png in (claims_png, kitchen_png):
        with Image.open(io.BytesIO(png)) as image:
            assert image.format == "PNG"
            assert image.width >= 1024
            assert image.height >= 576
    assert hashlib.sha256(claims_png).digest() != hashlib.sha256(kitchen_png).digest()


def test_renderer_rejects_gemini_image_provider(monkeypatch):
    monkeypatch.setenv("IMAGE_GENERATOR_PROVIDER", "gemini")
    service = ImageGenerationService()
    spec = _screen("SCREEN-001", 1, "Claims queue", "Triage claims.", "work_queue",
                   role="Claims examiner")

    with pytest.raises(RuntimeError, match="must use the local PyMuPDF renderer"):
        service.generate_screen_image(spec)


def test_renderer_rejects_invalid_png_bytes(monkeypatch):
    service = ImageGenerationService()
    spec = _screen("SCREEN-001", 1, "Claims queue", "Triage claims.", "work_queue",
                   role="Claims examiner")
    monkeypatch.setattr(service, "_render_enterprise_mockup", lambda spec, design: b"not an image")

    with pytest.raises(RuntimeError, match="invalid or unreadable PNG"):
        service.generate_screen_image(spec)
