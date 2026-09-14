import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from json_repair import repair_json
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.candidate_models = settings.gemini_candidate_models
        self.timeout = httpx.Timeout(settings.gemini_timeout_seconds, connect=10.0)

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
                "responseMimeType": "application/json",
                "maxOutputTokens": 8192
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
                    resp = None
                    for attempt in range(2):
                        try:
                            resp = client.post(url, json=request_body)
                            break
                        except httpx.RequestError as e:
                            last_error = e
                            if attempt == 0:
                                logger.warning(
                                    "Gemini network request failed for %s; retrying once: %s",
                                    model_name,
                                    e,
                                )
                                time.sleep(1)
                            else:
                                logger.error(
                                    "Gemini API is unreachable at generativelanguage.googleapis.com: %s",
                                    e,
                                )
                                raise RuntimeError(
                                    "Gemini API is unreachable. Check DNS, internet access, or firewall settings. "
                                    f"Cause: {e}"
                                ) from e

                    if resp is None:
                        continue
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            candidate = candidates[0]
                            content = candidate.get("content", {})
                            parts = content.get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
                            finish_reason = candidate.get("finishReason", "UNKNOWN")
                            prompt_feedback = data.get("promptFeedback", {})
                            block_reason = prompt_feedback.get("blockReason", "none")
                            last_error = RuntimeError(
                                "Gemini returned no text. "
                                f"finishReason={finish_reason}, blockReason={block_reason}"
                            )
                            logger.warning("Gemini model %s returned no text: %s", model_name, last_error)
                        else:
                            prompt_feedback = data.get("promptFeedback", {})
                            last_error = RuntimeError(
                                "Gemini returned no candidates. "
                                f"blockReason={prompt_feedback.get('blockReason', 'none')}"
                            )
                            logger.warning("Gemini model %s returned no candidates: %s", model_name, last_error)
                    else:
                        if resp.status_code == 429:
                            retry_match = re.search(
                                r"(?:retry in|retryDelay[\"']?\s*:\s*[\"']?)([0-9]+(?:\.[0-9]+)?)",
                                resp.text,
                                re.IGNORECASE,
                            )
                            retry_seconds = int(float(retry_match.group(1))) if retry_match else 60
                            message = (
                                "RESOURCE_EXHAUSTED: Gemini quota is exhausted for the configured project/model. "
                                f"Retry after approximately {retry_seconds} seconds, or configure a billed project/API key."
                            )
                            logger.warning(
                                "Gemini model %s returned HTTP 429; trying the next model without delay",
                                model_name,
                            )
                            last_error = RuntimeError(message)
                            continue
                        logger.warning(
                            "Gemini model %s returned HTTP %s: %s",
                            model_name,
                            resp.status_code,
                            resp.text
                        )
                        last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                except RuntimeError:
                    raise
                except Exception as e:
                    last_error = e
                    logger.warning("Gemini model %s call failed: %s", model_name, e)

        raise RuntimeError(
            f"Failed to generate content with Gemini API. Check GEMINI_API_KEY and Gemini model availability. "
            f"Cause: {last_error}"
        )

    def generate_dict(self, prompt_text: str) -> Dict[str, Any]:
        raw_output = self.generate_content(prompt_text)
        cleaned_json = self.clean_json(raw_output)
        try:
            parsed = self.parse_json(cleaned_json)
            if isinstance(parsed, dict):
                return parsed
            elif isinstance(parsed, list):
                return {"items": parsed}
            return {}
        except Exception as e:
            logger.error("Failed to parse Gemini JSON: %s | Raw: %s", e, raw_output)
            raise RuntimeError(f"Invalid JSON from Gemini: {e}")

    def generate_structured(self, prompt_text: str, schema_cls: Type[T]) -> T:
        recovery_prompt = (
            "\n\nIMPORTANT RESPONSE RECOVERY: Return only one complete valid JSON object. "
            "Do not use markdown fences, explanations, or trailing text. "
            "Keep every required field concise so the JSON is complete."
        )
        last_error = None
        for attempt in range(2):
            raw_output = self.generate_content(prompt_text if attempt == 0 else prompt_text + recovery_prompt)
            cleaned_json = self.clean_json(raw_output)
            try:
                parsed = self.parse_json(cleaned_json)
                if isinstance(parsed, list):
                    raise ValueError("Expected JSON object, got list")
                return schema_cls.model_validate(parsed)
            except Exception as e:
                last_error = e
                logger.warning(
                    "Gemini returned invalid %s JSON on attempt %s: %s; response prefix=%r",
                    schema_cls.__name__,
                    attempt + 1,
                    e,
                    (raw_output or "")[:300],
                )

        raise RuntimeError(f"Invalid structured JSON response from Gemini: {last_error}")

    def generate_structured_list(self, prompt_text: str, item_schema_cls: Type[T]) -> List[T]:
        raw_output = self.generate_content(prompt_text)
        cleaned_json = self.clean_json(raw_output)
        try:
            parsed = self.parse_json(cleaned_json)
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
    def parse_json(value: str) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            repaired = repair_json(value)
            return json.loads(repaired)

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

        # Find the first complete JSON value and ignore trailing prose or JSON fragments.
        first_brace = s.find("{")
        first_bracket = s.find("[")
        start = -1
        if first_brace != -1 and first_bracket != -1:
            start = min(first_brace, first_bracket)
        elif first_brace != -1:
            start = first_brace
        elif first_bracket != -1:
            start = first_bracket

        if start != -1:
            candidate = s[start:]
            try:
                _, end = json.JSONDecoder().raw_decode(candidate)
                return candidate[:end]
            except json.JSONDecodeError:
                last_brace = s.rfind("}")
                last_bracket = s.rfind("]")
                end = max(last_brace, last_bracket)
                if end >= start:
                    s = s[start : end + 1]

        return s


gemini_service = GeminiService()
