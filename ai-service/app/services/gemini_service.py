import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.candidate_models = settings.gemini_candidate_models
        self.timeout = httpx.Timeout(45.0, connect=10.0)

    def generate_content(self, prompt_text: str) -> str:
        api_key = settings.gemini_api_key or self.api_key
        if not api_key or not api_key.strip():
            raise RuntimeError("GEMINI_API_KEY is missing. Cannot call Gemini API.")

        models_to_try: List[str] = []
        if settings.gemini_model and settings.gemini_model.strip():
            models_to_try.append(settings.gemini_model.strip())
        for m in self.candidate_models:
            if m not in models_to_try:
                models_to_try.append(m)

        request_body = {
            "contents": [
                {
                    "parts": [{"text": prompt_text}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        last_error = None
        with httpx.Client(timeout=self.timeout) as client:
            for model_name in models_to_try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                    f"?key={api_key.strip()}"
                )
                try:
                    resp = client.post(url, json=request_body)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
                    else:
                        logger.warning(
                            "Gemini model %s returned HTTP %s: %s",
                            model_name,
                            resp.status_code,
                            resp.text
                        )
                        last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                except Exception as e:
                    last_error = e
                    logger.warning("Gemini model %s call failed: %s", model_name, e)

        raise RuntimeError(
            f"Failed to generate content with Gemini API. Check GEMINI_API_KEY. Cause: {last_error}"
        )

    def generate_structured(self, prompt_text: str, schema_cls: Type[T]) -> T:
        raw_output = self.generate_content(prompt_text)
        cleaned_json = self.clean_json(raw_output)
        try:
            parsed = json.loads(cleaned_json)
            if isinstance(parsed, list):
                # When root is list, Pydantic type adapter or direct validation
                raise ValueError("Expected JSON object, got list")
            return schema_cls.model_validate(parsed)
        except Exception as e:
            logger.error("Failed to parse Gemini response as %s: %s | Raw: %s", schema_cls.__name__, e, raw_output)
            raise RuntimeError(f"Invalid structured JSON response from Gemini: {e}")

    def generate_structured_list(self, prompt_text: str, item_schema_cls: Type[T]) -> List[T]:
        raw_output = self.generate_content(prompt_text)
        cleaned_json = self.clean_json(raw_output)
        try:
            parsed = json.loads(cleaned_json)
            if isinstance(parsed, dict):
                # If wrapped inside a key e.g. {"testCases": [...]}
                for val in parsed.values():
                    if isinstance(val, list):
                        parsed = val
                        break
            if not isinstance(parsed, list):
                parsed = [parsed]
            return [item_schema_cls.model_validate(item) for item in parsed]
        except Exception as e:
            logger.error("Failed to parse Gemini response as list of %s: %s | Raw: %s", item_schema_cls.__name__, e, raw_output)
            raise RuntimeError(f"Invalid structured JSON list response from Gemini: {e}")

    @staticmethod
    def clean_json(raw: Optional[str]) -> str:
        if not raw:
            return "{}"
        s = raw.strip()
        if s.startswith("```json"):
            s = s[7:]
        elif s.startswith("```"):
            s = s[3:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()

        # Find outer braces / brackets
        first_brace = s.find("{")
        first_bracket = s.find("[")
        start = -1
        if first_brace != -1 and first_bracket != -1:
            start = min(first_brace, first_bracket)
        elif first_brace != -1:
            start = first_brace
        elif first_bracket != -1:
            start = first_bracket

        last_brace = s.rfind("}")
        last_bracket = s.rfind("]")
        end = max(last_brace, last_bracket)

        if start != -1 and end != -1 and end >= start:
            s = s[start : end + 1]

        return s


gemini_service = GeminiService()
