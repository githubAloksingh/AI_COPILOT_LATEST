import secrets

from fastapi import Header, HTTPException, status

from app.config import settings


def require_mock_screens_service_token(
    x_service_token: str | None = Header(default=None),
) -> None:
    expected_token = settings.mock_screens_service_token.strip()
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mock Screens service authentication is not configured.",
        )
    if not x_service_token or not secrets.compare_digest(x_service_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid service authentication is required.",
        )