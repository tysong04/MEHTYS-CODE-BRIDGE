import logging
from typing import Optional
from app.config import settings
from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    ProviderStatusResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    ProviderConfig,
    ProviderInfo,
)
from app.services.translators.base import (
    BaseTranslationProvider,
    ProviderUnavailableError,
    TranslationExecutionError,
)
from app.services.translators.mock import MockTranslationProvider
from app.services.translators.ollama import OllamaTranslationProvider
from app.services.translators.gemini import GeminiTranslationProvider

logger = logging.getLogger("mtcb.services.translation")


class TranslationService:
    def __init__(self, provider: Optional[BaseTranslationProvider] = None):
        if provider:
            self.default_provider = provider
        else:
            self.default_provider = self._create_default_provider()

    def _create_default_provider(self) -> BaseTranslationProvider:
        provider_type = settings.PROVIDER_TYPE.lower().strip()
        if provider_type == "mock":
            logger.info("Initializing TranslationService with MockTranslationProvider")
            return MockTranslationProvider()
        else:
            logger.info("Initializing TranslationService with OllamaTranslationProvider (model: %s)", settings.OLLAMA_MODEL)
            return OllamaTranslationProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                timeout=settings.OLLAMA_TIMEOUT_SECONDS
            )

    def set_provider(self, provider: BaseTranslationProvider) -> None:
        """Dynamically replace default provider (useful for testing or configuration switching)."""
        self.default_provider = provider

    def resolve_provider(self, config: Optional[ProviderConfig] = None) -> BaseTranslationProvider:
        """
        Instantiate and configure the translation provider requested by the user.
        Validates cloud consent and ensures keys remain in session memory only.
        """
        if not config or not config.provider:
            return self.default_provider

        provider_name = config.provider.lower().strip()

        if provider_name == "gemini":
            if not config.consent_granted:
                raise TranslationExecutionError(
                    "User consent is required before transmitting code to external cloud AI (Google Gemini)."
                )
            if not config.api_key or not config.api_key.strip():
                raise ProviderUnavailableError(
                    message="Google Gemini API key is required.",
                    setup_instructions="Open Provider Settings and enter your Gemini API key from https://aistudio.google.com"
                )
            return GeminiTranslationProvider(
                api_key=config.api_key,
                model=config.model or "gemini-3.8-flash",
                timeout=settings.GEMINI_TIMEOUT_SECONDS
            )

        elif provider_name == "ollama":
            return OllamaTranslationProvider(
                base_url=config.base_url or settings.OLLAMA_BASE_URL,
                model=config.model or settings.OLLAMA_MODEL,
                timeout=settings.OLLAMA_TIMEOUT_SECONDS
            )

        elif provider_name == "mock":
            return MockTranslationProvider(
                model_name=config.model or "mock-model-v1"
            )

        else:
            raise TranslationExecutionError(f"Unsupported translation provider: '{config.provider}'")

    async def test_provider(self, req: ProviderTestRequest) -> ProviderTestResponse:
        """
        Validates a provider connection and credentials without translating code.
        """
        provider_name = req.provider.lower().strip()

        if provider_name == "gemini":
            if not req.api_key or not req.api_key.strip():
                return ProviderTestResponse(
                    valid=False,
                    provider="gemini",
                    model=req.model or "gemini-3.8-flash",
                    message="API key is required.",
                    details="Please enter your Google Gemini API key.",
                    error_type="MissingApiKey"
                )
            gemini_provider = GeminiTranslationProvider(
                api_key=req.api_key,
                model=req.model or "gemini-3.8-flash"
            )
            return await gemini_provider.test_connection()

        elif provider_name == "ollama":
            ollama_provider = OllamaTranslationProvider(
                base_url=req.base_url or settings.OLLAMA_BASE_URL,
                model=req.model or settings.OLLAMA_MODEL
            )
            status = await ollama_provider.get_status()
            return ProviderTestResponse(
                valid=status.available,
                provider="ollama",
                model=status.model,
                message=status.details,
                details=status.setup_instructions,
                error_type=None if status.available else "OllamaUnavailable"
            )

        elif provider_name == "mock":
            return ProviderTestResponse(
                valid=True,
                provider="mock",
                model=req.model or "mock-model-v1",
                message="Mock provider is available for offline testing.",
                details=None,
                error_type=None
            )

        else:
            return ProviderTestResponse(
                valid=False,
                provider=req.provider,
                model=req.model or "",
                message=f"Unknown provider: '{req.provider}'.",
                details="Supported providers are 'ollama', 'gemini', and 'mock'.",
                error_type="UnsupportedProvider"
            )

    async def get_status(self) -> ProviderStatusResponse:
        """Retrieve live health and readiness of default configured provider."""
        return await self.default_provider.get_status()

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Orchestrate translation through the resolved provider.
        Does NOT log API keys, full code contents, or sensitive instructions.
        """
        provider = self.resolve_provider(request.provider_config)

        # Safe logging: mask provider info, never print keys or source code
        model_name = getattr(provider, "model", getattr(provider, "_model_name", "default"))
        logger.info(
            "Translation requested: %s -> %s (provider=%s, model=%s, code_size=%d bytes, instructions=%s)",
            request.source_lang.value,
            request.target_lang.value,
            provider.name,
            model_name,
            len(request.code.encode("utf-8")),
            "provided" if request.instructions else "none"
        )

        result = await provider.translate(
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            code=request.code,
            instructions=request.instructions
        )

        return TranslationResponse(
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            translated_code=result.translated_code,
            explanation=result.explanation,
            warnings=result.warnings,
            provider_info=ProviderInfo(
                provider=result.provider_name or provider.name,
                model=result.model,
                execution_time_ms=result.execution_time_ms,
                verified=False  # Crucial: Never claim AI generated code is verified
            )
        )


_service_instance: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = TranslationService()
    return _service_instance
