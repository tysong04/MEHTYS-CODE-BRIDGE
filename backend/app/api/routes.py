import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.config import settings
from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    ProviderStatusResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    HealthResponse,
)
from app.services.translation_service import TranslationService, get_translation_service
from app.services.translators.base import (
    ProviderUnavailableError,
    TranslationExecutionError,
)

logger = logging.getLogger("mtcb.api.routes")
router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Backend service health check."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        app_name=settings.APP_NAME
    )


@router.get("/providers/status", response_model=ProviderStatusResponse, tags=["Provider"])
async def provider_status(
    service: TranslationService = Depends(get_translation_service)
) -> ProviderStatusResponse:
    """Check translation provider daemon connectivity and model availability."""
    return await service.get_status()


@router.post(
    "/providers/test",
    response_model=ProviderTestResponse,
    status_code=status.HTTP_200_OK,
    tags=["Provider"]
)
async def test_provider_connection(
    request: ProviderTestRequest,
    service: TranslationService = Depends(get_translation_service)
) -> ProviderTestResponse:
    """Test credentials, models, and connectivity for a user-specified provider without translating code."""
    return await service.test_provider(request)


@router.post(
    "/translate",
    response_model=TranslationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Translation"],
    responses={
        400: {"description": "Invalid translation parameters"},
        422: {"description": "Validation error (e.g. empty code, identical languages)"},
        503: {"description": "Translation provider unavailable or model missing"},
        502: {"description": "Translation execution failed"},
    }
)
async def translate_code(
    request: TranslationRequest,
    service: TranslationService = Depends(get_translation_service)
) -> TranslationResponse:
    """
    Translate code snippet between supported languages.
    Ensures safe handling: untrusted user input is not executed.
    """
    try:
        response = await service.translate(request)
        return response
    except ProviderUnavailableError as e:
        logger.warning("Translation request failed: provider unavailable (%s)", e.message)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": e.message,
                "setup_instructions": e.setup_instructions,
                "error_type": "ProviderUnavailable"
            }
        )
    except TranslationExecutionError as e:
        logger.error("Translation execution failure: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": str(e),
                "error_type": "TranslationExecutionError"
            }
        )
    except Exception as e:
        logger.exception("Unexpected error during translation: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred during translation.",
                "error_type": "InternalServerError"
            }
        )
