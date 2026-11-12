import json
import logging
import re
import time
from contextvars import ContextVar
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
        self._last_used_model: ContextVar[Optional[str]] = ContextVar(
            f"gemini_last_used_model_{id(self)}", default=None
        )

    @property
    def last_used_model(self) -> Optional[str]:
        return self._last_used_model.get()

    def generate_content(
        self,
        prompt_text: str,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._last_used_model.set(None)
        api_key = settings.gemini_api_key or self.api_key
        if not api_key or not api_key.strip():
            raise RuntimeError("GEMINI_API_KEY is missing. Cannot call Gemini API.")

        models_to_try: List[str] = []
        if settings.gemini_model and settings.gemini_model.strip():
            models_to_try.append(settings.gemini_model.strip())
        for m in self.candidate_models:
            if m not in models_to_try:
                models_to_try.append(m)

        generation_config: Dict[str, Any] = {
            "responseMimeType": "application/json",
            "maxOutputTokens": 65536,
        }
        if response_schema is not None:
            generation_config["responseJsonSchema"] = response_schema

        request_body = {
            "contents": [
                {
                    "parts": [{"text": prompt_text}]
                }
            ],
            "generationConfig": generation_config,
        }

        model_errors: List[str] = []
        with httpx.Client(timeout=self.timeout) as client:
            for model_name in models_to_try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                )
                resp = None
                request_error: Optional[httpx.RequestError] = None
                for attempt in range(2):
                    try:
                        resp = client.post(
                            url,
                            json=request_body,
                            headers={"x-goog-api-key": api_key.strip()},
                        )
                        break
                    except httpx.RequestError as exc:
                        request_error = exc
                        if attempt == 0:
                            logger.warning(
                                "Gemini request failed for model %s with %s; retrying once",
                                model_name,
                                type(exc).__name__,
                            )
                            time.sleep(1)

                if request_error is not None:
                    diagnostic = f"{model_name}: network error ({type(request_error).__name__})"
                    model_errors.append(diagnostic)
                    logger.warning("Gemini model attempt failed: %s", diagnostic)
                    continue
                if resp is None:
                    continue

                try:
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            candidate = candidates[0]
                            content = candidate.get("content", {})
                            parts = content.get("parts", [])
                            if parts and "text" in parts[0]:
                                self._last_used_model.set(model_name)
                                return parts[0]["text"]
                            finish_reason = candidate.get("finishReason", "UNKNOWN")
                            prompt_feedback = data.get("promptFeedback", {})
                            block_reason = prompt_feedback.get("blockReason", "none")
                            diagnostic = (
                                f"{model_name}: no text "
                                f"(finishReason={finish_reason}, blockReason={block_reason})"
                            )
                        else:
                            prompt_feedback = data.get("promptFeedback", {})
                            diagnostic = (
                                f"{model_name}: no candidates "
                                f"(blockReason={prompt_feedback.get('blockReason', 'none')})"
                            )
                    else:
                        diagnostic = self._http_error_diagnostic(
                            model_name,
                            resp,
                            sensitive_values=(api_key.strip(), prompt_text),
                        )
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
                            diagnostic = f"{diagnostic}; {message}"
                    model_errors.append(diagnostic)
                    logger.warning("Gemini model attempt failed: %s", diagnostic)
                except Exception as exc:
                    diagnostic = f"{model_name}: response processing error ({type(exc).__name__})"
                    model_errors.append(diagnostic)
                    logger.warning("Gemini model attempt failed: %s", diagnostic)

        raise RuntimeError(
            "Failed to generate content with Gemini API. "
            "Per-model diagnostics: " + "; ".join(model_errors)
        )

    @staticmethod
    def _http_error_diagnostic(
        model_name: str,
        response: httpx.Response,
        sensitive_values: tuple = (),
    ) -> str:
        """Return useful provider diagnostics without logging request content."""
        diagnostics: Dict[str, Any] = {"model": model_name, "http_status": response.status_code}
        try:
            payload = response.json()
        except (ValueError, AttributeError):
            payload = {}
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        if not isinstance(error, dict):
            error = {}

        provider_code = error.get("code")
        if isinstance(provider_code, int):
            diagnostics["provider_code"] = provider_code
        for field in ("status", "message"):
            value = error.get(field)
            if isinstance(value, str):
                diagnostics[field] = GeminiService._sanitize_error_text(value, sensitive_values)

        error_details = error.get("details")
        if isinstance(error_details, list):
            diagnostics["details"] = GeminiService._sanitize_error_details(
                error_details,
                sensitive_values,
            )
        return json.dumps(diagnostics, ensure_ascii=True, separators=(",", ":"))[:4000]

    @staticmethod
    def _sanitize_error_text(value: str, sensitive_values: tuple = ()) -> str:
        sanitized = value
        for sensitive_value in sensitive_values:
            if sensitive_value:
                sanitized = sanitized.replace(sensitive_value, "[redacted]")
        sanitized = re.sub(
            r"(?i)(x-goog-api-key|authorization|api[_ -]?key)(\s*[:=]\s*)[^\s,;]+",
            r"\1\2[redacted]",
            sanitized,
        )
        sanitized = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[redacted]", sanitized)
        return sanitized[:2000]

    @staticmethod
    def _sanitize_error_details(details: list, sensitive_values: tuple = ()) -> list:
        allowed_fields = {
            "@type",
            "field",
            "description",
            "fieldViolations",
            "violations",
            "reason",
            "domain",
            "metadata",
            "locale",
            "quotaLimit",
            "quota_limit",
            "quotaLocation",
            "quota_location",
            "service",
            "method",
            "consumer",
            "retryDelay",
            "retry_delay",
        }

        def sanitize(value: Any) -> Any:
            if isinstance(value, dict):
                return {
                    key: sanitize(item)
                    for key, item in value.items()
                    if key in allowed_fields and isinstance(key, str)
                }
            if isinstance(value, list):
                return [sanitize(item) for item in value[:20]]
            if isinstance(value, str):
                return GeminiService._sanitize_error_text(value, sensitive_values)
            if isinstance(value, (int, float, bool)) or value is None:
                return value
            return None

        return [sanitize(item) for item in details[:10]]

    def generate_dict(
        self,
        prompt_text: str,
        response_schema: Optional[Dict[str, Any]] = None,
        require_object: bool = False,
    ) -> Dict[str, Any]:
        raw_output = self.generate_content(prompt_text, response_schema=response_schema)
        if not raw_output or not raw_output.strip():
            raise RuntimeError("Invalid JSON from Gemini: empty response")
        cleaned_json = self.clean_json(raw_output)
        try:
            parsed = self.parse_json(cleaned_json)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list) and not require_object:
                return {"items": parsed}
            if isinstance(parsed, list):
                raise ValueError("Expected a JSON object but received an array.")
            raise ValueError(f"Expected a JSON object but received {type(parsed).__name__}.")
        except (ValueError, TypeError) as e:
            logger.error("Failed to parse Gemini JSON (%s)", type(e).__name__)
            raise RuntimeError(f"Invalid JSON from Gemini: {type(e).__name__}.")

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
                    "Gemini returned invalid %s JSON on attempt %s (%s)",
                    schema_cls.__name__,
                    attempt + 1,
                    type(e).__name__,
                )

        raise RuntimeError(
            "Invalid structured JSON response from Gemini after two attempts "
            f"({type(last_error).__name__ if last_error else 'unknown error'})."
        )

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
            logger.error(
                "Failed to parse Gemini response as list of %s (%s)",
                item_schema_cls.__name__,
                type(e).__name__,
            )
            raise RuntimeError(
                "Invalid structured JSON list response from Gemini "
                f"({type(e).__name__})."
            )

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
