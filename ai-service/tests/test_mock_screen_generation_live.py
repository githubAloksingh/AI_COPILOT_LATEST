import hashlib
import os

import pytest
from PIL import Image

from app.services.image_generation_service import image_generation_service
from app.services.screen_plan_service import screen_plan_service


@pytest.mark.skipif(
    os.getenv("RUN_GEMINI_MOCK_SCREEN_INTEGRATION") != "1",
    reason="Set RUN_GEMINI_MOCK_SCREEN_INTEGRATION=1 to run live Gemini text planning and local rendering.",
)
def test_distinct_requirements_generate_distinct_real_mockup_images(tmp_path):
    healthcare_brd = """
    Product: Harbor Claims Adjudication.
    Claims examiners review medical claims, validate member eligibility and diagnosis
    codes, inspect submitted clinical documents, apply coverage rules, and refer
    high-value or suspicious claims to a senior reviewer. The adjudication queue
    must prioritize service-level deadlines and show claim number, member, provider,
    submitted amount, plan, diagnosis, evidence status, and assigned examiner.
    Examiners can request missing evidence, approve covered services, deny claims
    with a reason code, or escalate for medical review. Supervisors resolve
    escalations and monitor turnaround time, denial reasons, and outstanding claims.
    """
    restaurant_brd = """
    Product: Juniper Kitchen Operations.
    Restaurant staff receive dine-in, pickup, and delivery orders. The kitchen lead
    dispatches meal tickets to stations, tracks preparation time, and prioritizes
    orders by promised pickup time. Tickets show order number, table or pickup name,
    item modifiers, allergy warnings, station, and elapsed time. Cooks can mark
    individual items started and ready; the expediter holds an order until all items
    are ready. Front-of-house staff manage table seating and notify customers when
    pickup orders are ready. Managers review sales by menu item, waste, and service
    time by shift.
    """

    healthcare_plan = screen_plan_service.generate_plan(healthcare_brd, "Harbor Claims")
    restaurant_plan = screen_plan_service.generate_plan(restaurant_brd, "Juniper Kitchen")

    assert healthcare_plan.screens
    assert restaurant_plan.screens
    healthcare_specs = " ".join(
        f"{screen.name} {screen.purpose} "
        + " ".join(field.label for field in screen.fields)
        for screen in healthcare_plan.screens
    ).lower()
    restaurant_specs = " ".join(
        f"{screen.name} {screen.purpose} "
        + " ".join(field.label for field in screen.fields)
        for screen in restaurant_plan.screens
    ).lower()
    assert any(term in healthcare_specs for term in ("claim", "member", "adjudicat", "diagnosis"))
    assert any(term in restaurant_specs for term in ("order", "kitchen", "ticket", "station"))

    healthcare_image = image_generation_service.generate_screen_image(
        healthcare_plan.screens[0], healthcare_plan.design_context
    )
    restaurant_image = image_generation_service.generate_screen_image(
        restaurant_plan.screens[0], restaurant_plan.design_context
    )
    healthcare_path = tmp_path / "healthcare-mockup.png"
    restaurant_path = tmp_path / "restaurant-mockup.png"
    healthcare_path.write_bytes(healthcare_image)
    restaurant_path.write_bytes(restaurant_image)

    for image_path in (healthcare_path, restaurant_path):
        with Image.open(image_path) as image:
            assert image.format == "PNG"
            assert image.width >= 1024
            assert image.height >= 576

    assert hashlib.sha256(healthcare_image).digest() != hashlib.sha256(restaurant_image).digest()
    print(f"Inspect generated mockups: {healthcare_path} and {restaurant_path}")
