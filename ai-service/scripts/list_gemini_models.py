"""List Gemini models available to the configured key without generating content."""

import sys
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.config import settings


LIST_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT_SECONDS = 30.0


def parse_model_list(payload: Any) -> List[Dict[str, Any]]:
    """Keep only model names and supported generation methods from ListModels."""
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise ValueError("Invalid ListModels response: expected a models list.")

    models = []
    for model in payload["models"]:
        if not isinstance(model, dict):
            continue
        name = model.get("name")
        methods = model.get("supportedGenerationMethods")
        if not isinstance(name, str) or not isinstance(methods, list):
            continue
        models.append({
            "name": name,
            "supportedGenerationMethods": [
                method for method in methods if isinstance(method, str)
            ],
        })
    return models


def models_supporting_generate_content(
    models: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return [
        model for model in models
        if "generateContent" in model["supportedGenerationMethods"]
    ]


def list_available_models(
    api_key: str,
    http_get: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    if http_get is None:
        http_get = httpx.get
    response = http_get(
        LIST_MODELS_URL,
        headers={"x-goog-api-key": api_key},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return parse_model_list(response.json())


def main() -> int:
    api_key = settings.gemini_api_key.strip()
    if not api_key:
        print("GEMINI_API_KEY is not configured.", file=sys.stderr)
        return 1

    try:
        models = list_available_models(api_key)
    except httpx.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else "unavailable"
        print(f"Gemini ListModels request failed (HTTP {status_code}).", file=sys.stderr)
        return 1
    except (ValueError, TypeError):
        print("Gemini ListModels returned an invalid response.", file=sys.stderr)
        return 1

    print("Available v1beta models (model name | supported generation methods):")
    for model in models:
        methods = ", ".join(model["supportedGenerationMethods"]) or "(none)"
        print(f'{model["name"]} | {methods}')

    compatible = models_supporting_generate_content(models)
    print("\nModels compatible with the current v1beta generateContent call:")
    for model in compatible:
        print(model["name"])
    if not compatible:
        print("(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
