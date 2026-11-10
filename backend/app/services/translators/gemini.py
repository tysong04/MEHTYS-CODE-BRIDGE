import asyncio
import json
import logging
import re
import time
from typing import Optional, List, Dict, Any
import httpx

from app.schemas.translation import (
    Language,
    ProviderStatusResponse,
    ProviderTestResponse,
    ModelOption,
)
from app.services.translators.base import (
    BaseTranslationProvider,
    TranslationResult,
    ProviderUnavailableError,
    TranslationExecutionError,
)
from app.services.translators.policy import build_translation_prompt

logger = logging.getLogger("mtcb.translators.gemini")

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
FALLBACK_SUGGESTIONS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro", "gemini-flash-latest"]
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Strict schema to accelerate JSON generation and avoid parsing latency
TRANSLATION_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "translated_code": {
            "type": "STRING",
            "description": "The faithfully translated code adhering strictly to policy."
        },
        "explanation": {
            "type": "STRING",
            "description": "Concise summary of necessary syntax adaptations."
        },
        "warnings": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "List of behavioral differences, potential source bugs, or platform caveats."
        }
    },
    "required": ["translated_code"]
}


def _build_generation_config(model: str, include_schema: bool = True, low_latency: bool = True) -> Dict[str, Any]:
    """
    Constructs an optimized generationConfig.
    For Gemini 3/4: Sets thinkingLevel to 'low' to avoid unconstrained multi-minute reasoning.
    For Gemini 2.5: Sets thinkingBudget to 0 to disable thinking for maximum speed.
    """
    config: Dict[str, Any] = {
        "temperature": 0.2,
        "responseMimeType": "application/json"
    }
    if include_schema:
        config["responseSchema"] = TRANSLATION_RESPONSE_SCHEMA

    if low_latency:
        clean = model.lower().replace("models/", "").strip()
        if "gemini-3" in clean or "gemini-4" in clean:
            # Low reasoning level drastically cuts Time-To-First-Token (TTFT)
            config["thinkingConfig"] = {
                "thinkingLevel": "low"
            }
        elif "gemini-2.5" in clean:
            # 0 disables thinking on Gemini 2.5 flash
            config["thinkingConfig"] = {
                "thinkingBudget": 0
            }

    return config


class GeminiTranslationProvider(BaseTranslationProvider):
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        timeout: float = 60.0
    ):
        if not api_key or not api_key.strip():
            raise ProviderUnavailableError(
                message="Google Gemini API key is required.",
                setup_instructions="Provide your Google Gemini API key in Provider Settings (get a free key at https://aistudio.google.com)."
            )
        self.api_key = api_key.strip()
        self.model = (model or DEFAULT_GEMINI_MODEL).strip()
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "gemini"

    async def get_status(self) -> ProviderStatusResponse:
        """Verify API key validity and model accessibility with Google Gemini REST API."""
        test_result = await self.test_connection()
        return ProviderStatusResponse(
            provider="gemini",
            available=test_result.valid,
            model=self.model,
            details=test_result.message,
            setup_instructions=test_result.details if not test_result.valid else None
        )

    async def test_connection(self) -> ProviderTestResponse:
        """
        Actively test the Gemini API key against Google's models discovery endpoint.
        Dynamically discovers models supporting generateContent and verifies accessibility.
        Does NOT expose the API key in error messages or logs.
        """
        # Endpoint: GET /v1beta/models
        url = f"{GEMINI_API_BASE}/models"
        headers = {
            "x-goog-api-key": self.api_key,
            "User-Agent": "MTCB-MehtysCodeBridge/0.1.0"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=headers)

                if res.status_code == 200:
                    data = res.json()
                    raw_models = data.get("models", [])

                    # Dynamically filter models supporting generateContent
                    available_options: List[ModelOption] = []
                    available_ids: List[str] = []
                    for m in raw_models:
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            full_name = m.get("name", "")
                            m_id = full_name.replace("models/", "").strip()
                            d_name = m.get("displayName", m_id)
                            available_options.append(ModelOption(id=m_id, label=f"{d_name} ({m_id})"))
                            available_ids.append(m_id)

                    if not available_ids:
                        return ProviderTestResponse(
                            valid=False,
                            provider="gemini",
                            model=self.model,
                            message="API key verified, but no models supporting 'generateContent' were returned.",
                            details="Ensure Generative Language API is enabled on your project in Google Cloud / AI Studio.",
                            error_type="NoAvailableModels",
                            available_models=[]
                        )

                    # Check if configured model is in the available list
                    clean_model = self.model.replace("models/", "").strip()
                    model_found = clean_model in available_ids or any(
                        m.endswith(f"/{clean_model}") for m in available_ids
                    )

                    if clean_model and not model_found:
                        # Recommend a model that actually exists in available_ids, NOT the failed model
                        recommended = "gemini-3.8-flash" if "gemini-3.8-flash" in available_ids else available_ids[0]
                        sample_available = [m for m in available_ids if m != clean_model][:4]
                        return ProviderTestResponse(
                            valid=False,
                            provider="gemini",
                            model=self.model,
                            message=f"Model '{self.model}' is not available for this API key. Recommended alternative: '{recommended}'.",
                            details=f"Your key has access to {len(available_ids)} models, including: {', '.join(sample_available)}. Please select an active model in settings.",
                            error_type="ModelUnavailable",
                            available_models=available_options
                        )

                    return ProviderTestResponse(
                        valid=True,
                        provider="gemini",
                        model=self.model,
                        message=f"Connected successfully to Google Gemini. Verified access to {len(available_ids)} active models.",
                        details=None,
                        error_type=None,
                        available_models=available_options
                    )

                elif res.status_code in (400, 401):
                    return ProviderTestResponse(
                        valid=False,
                        provider="gemini",
                        model=self.model,
                        message="Invalid Google Gemini API key.",
                        details="Please verify your API key from Google AI Studio (https://aistudio.google.com).",
                        error_type="InvalidApiKey"
                    )
                elif res.status_code == 403:
                    return ProviderTestResponse(
                        valid=False,
                        provider="gemini",
                        model=self.model,
                        message="API key forbidden or permission denied.",
                        details="Ensure the API key has Generative Language API enabled and is not IP or referer restricted.",
                        error_type="Forbidden"
                    )
                elif res.status_code == 429:
                    return ProviderTestResponse(
                        valid=False,
                        provider="gemini",
                        model=self.model,
                        message="Gemini API rate limit or quota exceeded.",
                        details="Check your current quota in Google AI Studio or wait before retrying.",
                        error_type="QuotaExceeded"
                    )
                else:
                    return ProviderTestResponse(
                        valid=False,
                        provider="gemini",
                        model=self.model,
                        message=f"Gemini API returned HTTP {res.status_code}.",
                        details="An unexpected response was received from Google Gemini.",
                        error_type="HttpError"
                    )

        except (httpx.ConnectError, httpx.NetworkError):
            return ProviderTestResponse(
                valid=False,
                provider="gemini",
                model=self.model,
                message="Cannot connect to Google Gemini API.",
                details="Network connection failed. Check your internet access and proxy settings.",
                error_type="NetworkError"
            )
        except httpx.TimeoutException:
            return ProviderTestResponse(
                valid=False,
                provider="gemini",
                model=self.model,
                message="Connection to Google Gemini API timed out.",
                details="Request exceeded 10 seconds. Check network latency.",
                error_type="Timeout"
            )
        except Exception as e:
            logger.exception("Unexpected error during Gemini connection test")
            return ProviderTestResponse(
                valid=False,
                provider="gemini",
                model=self.model,
                message="Connection test failed due to an unexpected error.",
                details=f"Error type: {type(e).__name__}",
                error_type="UnexpectedError"
            )

    async def translate(
        self,
        source_lang: Language,
        target_lang: Language,
        code: str,
        instructions: Optional[str] = None
    ) -> TranslationResult:
        clean_model = self.model.replace("models/", "").strip()
        url = f"{GEMINI_API_BASE}/models/{clean_model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "MTCB-MehtysCodeBridge/0.1.0"
        }

        prompt = self._build_prompt(source_lang, target_lang, code, instructions)

        # Granular timeout: 15s connect/pool, full timeout for read
        timeout_config = httpx.Timeout(
            timeout=self.timeout,
            connect=15.0,
            read=self.timeout,
            write=15.0,
            pool=15.0
        )

        # First attempt with low-latency thinking config and response schema;
        # if rejected with 400 (e.g. unsupported thinking/schema field on some models), fallback to basic config.
        gen_configs = [
            _build_generation_config(clean_model, include_schema=True, low_latency=True),
            _build_generation_config(clean_model, include_schema=False, low_latency=False),
        ]

        part_text = ""
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=timeout_config) as client:
            for cfg_idx, gen_config in enumerate(gen_configs):
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}]
                        }
                    ],
                    "generationConfig": gen_config
                }

                try:
                    res = await client.post(url, headers=headers, json=payload)

                    # Check for 400 with invalid schema/thinking arguments vs invalid API key
                    if res.status_code == 400:
                        err_body = res.text.lower()
                        if "api_key" in err_body or "key not valid" in err_body:
                            self._handle_http_error(res)
                        elif cfg_idx == 0 and any(k in err_body for k in ("thinking", "schema", "generation_config", "unknown field", "invalid_argument")):
                            logger.warning(
                                "Gemini model '%s' rejected advanced generationConfig. Retrying with basic configuration.",
                                clean_model
                            )
                            continue
                        else:
                            self._handle_http_error(res)

                    # Transient server error retry (HTTP 503)
                    if res.status_code == 503:
                        logger.warning("Gemini returned HTTP 503. Retrying once after 1s...")
                        await asyncio.sleep(1.0)
                        res = await client.post(url, headers=headers, json=payload)

                    if res.status_code != 200:
                        self._handle_http_error(res)

                    data = res.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        block_reason = data.get("promptFeedback", {}).get("blockReason", "Unknown")
                        raise TranslationExecutionError(
                            f"Gemini did not return any translation candidates (Block reason: {block_reason})."
                        )

                    # Filter out internal reasoning parts (thought: True) to retrieve the actual output
                    parts = candidates[0].get("content", {}).get("parts", [])
                    output_parts = [p.get("text", "") for p in parts if not p.get("thought", False) and p.get("text")]
                    part_text = "\n".join(output_parts).strip()
                    if not part_text and parts:
                        part_text = parts[-1].get("text", "").strip()

                    if not part_text:
                        raise TranslationExecutionError("Gemini returned an empty response.")

                    break  # Success!

                except httpx.ConnectError as e:
                    raise ProviderUnavailableError(
                        "Unable to connect to Google Gemini API. Please check your internet connection.",
                        "Ensure your machine has internet access to reach https://generativelanguage.googleapis.com"
                    ) from e
                except httpx.ReadTimeout as e:
                    raise TranslationExecutionError(
                        f"Translation timed out after {self.timeout}s while waiting for Google Gemini response."
                    ) from e
                except (ProviderUnavailableError, TranslationExecutionError):
                    raise
                except Exception as e:
                    raise TranslationExecutionError(
                        f"Unexpected error communicating with Google Gemini: {type(e).__name__}"
                    ) from e

        if not part_text:
            raise TranslationExecutionError("Gemini translation returned no content.")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info("Gemini translation completed for model '%s' in %.2fms", clean_model, elapsed_ms)

        translated_code, explanation, warnings = self._parse_response(part_text, source_lang, target_lang)
        warnings.append("AI translations may contain subtle behavioral differences. Review before running.")

        return TranslationResult(
            translated_code=translated_code,
            explanation=explanation,
            warnings=warnings,
            model=self.model,
            provider_name="gemini",
            execution_time_ms=round(elapsed_ms, 2)
        )

    def _handle_http_error(self, res: httpx.Response) -> None:
        err_msg = ""
        try:
            err_json = res.json()
            err_msg = err_json.get("error", {}).get("message", "")
        except Exception:
            err_msg = res.text[:200] if res.text else ""

        if res.status_code == 400:
            if "api_key" in err_msg.lower() or "key not valid" in err_msg.lower():
                raise ProviderUnavailableError(
                    "Google Gemini rejected the request: Invalid API key.",
                    "Verify your API key from Google AI Studio (https://aistudio.google.com)."
                )
            raise TranslationExecutionError(
                f"Google Gemini request failed (Bad Request): {err_msg or 'Invalid request parameters.'}"
            )
        elif res.status_code == 401:
            raise ProviderUnavailableError(
                "Google Gemini rejected the request: Invalid API key.",
                "Verify your API key from Google AI Studio (https://aistudio.google.com)."
            )
        elif res.status_code == 403:
            raise TranslationExecutionError(
                "Google Gemini request forbidden or quota suspended for this API key."
            )
        elif res.status_code == 404:
            clean_model = self.model.replace("models/", "").strip()
            alt_candidates = [m for m in FALLBACK_SUGGESTIONS if m != clean_model]
            suggestions = f" (such as {', '.join(alt_candidates[:2])})" if alt_candidates else ""
            raise TranslationExecutionError(
                f"Configured Gemini model '{self.model}' was not found or is unavailable for your API key. "
                f"Please open Provider Settings to select an active model{suggestions} or click 'Test Connection' to refresh your available models."
            )
        elif res.status_code == 429:
            raise TranslationExecutionError(
                "Google Gemini API rate limit or quota exceeded. Please wait a moment before trying again."
            )
        elif res.status_code >= 500:
            raise TranslationExecutionError(
                f"Google Gemini service is temporarily unavailable (HTTP {res.status_code})."
            )
        else:
            raise TranslationExecutionError(
                f"Gemini API returned an unexpected error (HTTP {res.status_code})."
            )

    def _build_prompt(
        self,
        source_lang: Language,
        target_lang: Language,
        code: str,
        instructions: Optional[str]
    ) -> str:
        return build_translation_prompt(
            source_lang=source_lang,
            target_lang=target_lang,
            code=code,
            instructions=instructions
        )

    def _parse_response(
        self,
        text: str,
        source_lang: Language,
        target_lang: Language
    ) -> tuple[str, str, List[str]]:
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, dict) and "translated_code" in parsed:
                translated_code = str(parsed.get("translated_code", ""))
                explanation = str(parsed.get("explanation", "Translation completed."))
                warnings = parsed.get("warnings", [])
                if not isinstance(warnings, list):
                    warnings = [str(warnings)] if warnings else []
                return translated_code, explanation, [str(w) for w in warnings]
        except json.JSONDecodeError:
            pass

        # Fallback if model output contained markdown code fences
        fence_match = re.search(r"```(?:[a-zA-Z0-9_\-\+]+)?\s*([\s\S]*?)```", text)
        if fence_match:
            translated_code = fence_match.group(1).strip()
            explanation = re.sub(r"```[\s\S]*?```", "", text).strip() or f"Translated from {source_lang.value} to {target_lang.value}."
            return translated_code, explanation, ["Parsed code from markdown output."]

        return text.strip(), f"Translated from {source_lang.value} to {target_lang.value}.", ["Raw model response parsed."]
