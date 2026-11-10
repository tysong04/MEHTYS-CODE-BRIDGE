import json
import logging
import re
import time
from typing import Optional, List, Dict, Any
import httpx

from app.config import settings
from app.schemas.translation import Language, ProviderStatusResponse
from app.services.translators.base import (
    BaseTranslationProvider,
    TranslationResult,
    ProviderUnavailableError,
    TranslationExecutionError,
)
from app.services.translators.policy import build_translation_prompt

logger = logging.getLogger("mtcb.translators.ollama")


def normalize_ollama_tag(tag: str) -> tuple[str, str]:
    """
    Normalizes an Ollama model identifier into a (model_name, tag) tuple.
    
    Examples:
      'qwen2.5-coder:7b'                            -> ('qwen2.5-coder', '7b')
      'qwen2.5-coder'                               -> ('qwen2.5-coder', 'latest')
      'registry.ollama.ai/library/qwen2.5-coder:7b' -> ('qwen2.5-coder', '7b')
      'library/qwen2.5-coder:latest'                -> ('qwen2.5-coder', 'latest')
    """
    clean = tag.strip().lower()
    if "/" in clean:
        clean = clean.split("/")[-1]
    if ":" in clean:
        name, version = clean.split(":", 1)
        return name.strip(), version.strip()
    return clean.strip(), "latest"


def matches_ollama_model(configured_model: str, available_model: str) -> bool:
    """
    Determines whether an available Ollama model tag matches the configured model,
    avoiding false positives from partial substring matches (e.g. 7b vs 1.5b).
    """
    conf_name, conf_tag = normalize_ollama_tag(configured_model)
    avail_name, avail_tag = normalize_ollama_tag(available_model)
    return conf_name == avail_name and conf_tag == avail_tag


class OllamaTranslationProvider(BaseTranslationProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    @property
    def name(self) -> str:
        return "ollama"

    async def get_status(self) -> ProviderStatusResponse:
        """Check if the Ollama daemon is reachable and whether the configured model exists."""
        tags_url = f"{self.base_url}/api/tags"
        setup_guide = (
            f"1. Download and install Ollama from https://ollama.com\n"
            f"2. Start the Ollama service: `ollama serve`\n"
            f"3. Pull the code model: `ollama pull {self.model}`"
        )

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(tags_url)
                if response.status_code != 200:
                    return ProviderStatusResponse(
                        provider="ollama",
                        available=False,
                        model=self.model,
                        details=f"Ollama server returned HTTP {response.status_code}.",
                        setup_instructions=setup_guide
                    )

                data = response.json()
                models = data.get("models", [])
                # Tag names might be e.g. "qwen2.5-coder:7b" or "qwen2.5-coder:latest"
                available_model_names = [m.get("name", "") for m in models]

                # Check if configured model matches any available models using normalized tags
                has_model = any(
                    matches_ollama_model(self.model, name)
                    for name in available_model_names
                )

                if not has_model:
                    return ProviderStatusResponse(
                        provider="ollama",
                        available=False,
                        model=self.model,
                        details=f"Ollama is running, but model '{self.model}' was not found locally. Available models: {available_model_names or 'none'}.",
                        setup_instructions=f"Run command: `ollama pull {self.model}`"
                    )

                return ProviderStatusResponse(
                    provider="ollama",
                    available=True,
                    model=self.model,
                    details=f"Ollama is running and model '{self.model}' is available.",
                    setup_instructions=None
                )

        except (httpx.ConnectError, httpx.NetworkError):
            return ProviderStatusResponse(
                provider="ollama",
                available=False,
                model=self.model,
                details=f"Cannot connect to Ollama at {self.base_url}. Service is offline or not installed.",
                setup_instructions=setup_guide
            )
        except Exception as e:
            logger.warning("Error checking Ollama status: %s", type(e).__name__)
            return ProviderStatusResponse(
                provider="ollama",
                available=False,
                model=self.model,
                details=f"Ollama check encountered an unexpected error: {type(e).__name__}.",
                setup_instructions=setup_guide
            )

    async def translate(
        self,
        source_lang: Language,
        target_lang: Language,
        code: str,
        instructions: Optional[str] = None
    ) -> TranslationResult:
        # First verify availability
        status = await self.get_status()
        if not status.available:
            raise ProviderUnavailableError(
                message=status.details,
                setup_instructions=status.setup_instructions
            )

        prompt = self._build_prompt(source_lang, target_lang, code, instructions)
        generate_url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
            }
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(generate_url, json=payload)
                if response.status_code != 200:
                    raise TranslationExecutionError(
                        f"Ollama translation request failed with status HTTP {response.status_code}: {response.text[:200]}"
                    )

                raw_json = response.json()
                response_text = raw_json.get("response", "")

        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise ProviderUnavailableError(
                f"Lost connection to Ollama server at {self.base_url}.",
                setup_instructions=status.setup_instructions
            ) from e
        except httpx.ReadTimeout as e:
            raise TranslationExecutionError(
                f"Translation timed out after {self.timeout}s while waiting for Ollama model '{self.model}'."
            ) from e
        except Exception as e:
            if isinstance(e, (ProviderUnavailableError, TranslationExecutionError)):
                raise
            raise TranslationExecutionError(f"Unexpected error communicating with Ollama: {str(e)}") from e

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        translated_code, explanation, warnings = self._parse_response(
            response_text,
            source_lang,
            target_lang
        )

        # Standard safety warning appended to all outputs
        warnings.append("AI translations may contain subtle semantic differences. Review before running.")

        return TranslationResult(
            translated_code=translated_code,
            explanation=explanation,
            warnings=warnings,
            model=self.model,
            provider_name="ollama",
            execution_time_ms=round(elapsed_ms, 2)
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

        # Fallback if model output was not valid JSON: extract code fences
        logger.info("JSON parsing failed on model response; falling back to pattern extraction.")
        fence_match = re.search(r"```(?:[a-zA-Z0-9_\-\+]+)?\s*([\s\S]*?)```", text)
        if fence_match:
            translated_code = fence_match.group(1).strip()
            # Everything outside the fence can be explanation
            explanation = re.sub(r"```[\s\S]*?```", "", text).strip() or f"Translated from {source_lang.value} to {target_lang.value}."
            return translated_code, explanation, ["Output parsed using code fence fallback."]

        # If completely raw
        return text.strip(), f"Translated from {source_lang.value} to {target_lang.value}.", ["Raw model response parsed."]
