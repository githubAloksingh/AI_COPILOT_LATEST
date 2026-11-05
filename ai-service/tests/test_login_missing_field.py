import pytest

from app.services.screen_plan_service import (
    ScreenPlanService,
    ScreenPlanValidationError,
)

def test_login_requirement_missing_screen_field_raises_validation_error():
    service = ScreenPlanService()
    brd = (
        "The system shall provide a Login screen with a Customer ID/Username "
        "field and a Password field. "
        "The Login screen shall include a Remember Me checkbox."
    )
    plan_data = {
        "application_name": "TestApp",
        "application_summary": "Test summary",
        "global_navigation": {"navigation_items": []},
        "screens": [
            {
                "name": "Login",
                "purpose": "Authenticate user",
                "screen_type": "form",
                "source_evidence": [brd],
                "fields": [
                    {"label": "Customer ID/Username", "type": "text"},
                    {"label": "Remember Me", "type": "text"},
                ],
                "actions": [],
            }
        ],
    }
    with pytest.raises(ScreenPlanValidationError) as exc:
        service._parse_and_validate_plan(plan_data, source_text=brd)
    assert "screen_fields 'Password'" in str(exc.value)
