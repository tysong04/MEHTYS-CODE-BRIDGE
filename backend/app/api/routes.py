import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from app.config import settings
from app.schemas.translation import (
    TranslationRequest,
    TranslationResponse,
    ProviderStatusResponse,
    ProviderTestRequest,
    ProviderTestResponse,
    HealthResponse,
)
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserProfile,
)
from app.schemas.execution import (
    ExecuteRequest,
    ExecuteResponse,
)
from app.services.auth_service import (
    register_user,
    authenticate_user,
    get_user_from_token,
    invalidate_session,
)
from app.services.execution_service import execute_python_code
from app.services.translation_service import TranslationService, get_translation_service
from app.services.translators.base import (
    ProviderUnavailableError,
    TranslationExecutionError,
)

logger = logging.getLogger("mtcb.api.routes")
router = APIRouter(prefix="/api")


def extract_bearer_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Helper to extract bearer token from Authorization header."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"]
)
async def register(request: RegisterRequest) -> AuthResponse:
    """Register a new user account with secure password hashing."""
    try:
        data = register_user(request.name, request.email, request.password)
        return AuthResponse(
            user=UserProfile(**data["user"]),
            token=data["token"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "error_type": "RegistrationError"}
        )


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"]
)
async def login(request: LoginRequest) -> AuthResponse:
    """Authenticate with email and password to receive a session token."""
    try:
        data = authenticate_user(request.email, request.password)
        return AuthResponse(
            user=UserProfile(**data["user"]),
            token=data["token"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e), "error_type": "AuthenticationError"}
        )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    tags=["Authentication"]
)
async def logout(token: Optional[str] = Depends(extract_bearer_token)):
    """Invalidate session token."""
    if token:
        invalidate_session(token)
    return {"status": "success", "message": "Logged out successfully."}


@router.get(
    "/auth/me",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"]
)
async def get_current_user_profile(token: Optional[str] = Depends(extract_bearer_token)) -> UserProfile:
    """Retrieve profile for the authenticated session."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Authorization token required.", "error_type": "Unauthorized"}
        )
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Session expired or invalid. Please log in again.", "error_type": "SessionExpired"}
        )
    return UserProfile(**user)


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    status_code=status.HTTP_200_OK,
    tags=["Execution"]
)
async def execute_code(request: ExecuteRequest) -> ExecuteResponse:
    """
    Safely execute a code snippet in an isolated, resource-constrained sandbox.
    Currently supports Python via isolated subprocess. JavaScript is executed
    client-side in a Web Worker, but can be routed here as well.
    """
    lang = request.language.lower().strip()
    if lang == "python":
        res = execute_python_code(request.code, stdin_data=request.stdin or "")
        return ExecuteResponse(**res)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Server-side execution is only configured for Python. JavaScript runs safely in the browser Web Worker.",
                "error_type": "UnsupportedExecutionLanguage"
            }
        )


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
