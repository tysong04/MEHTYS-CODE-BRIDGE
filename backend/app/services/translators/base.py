from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass, field
from app.schemas.translation import Language, ProviderStatusResponse


class ProviderUnavailableError(Exception):
    """Raised when the translation provider service/daemon is not reachable or configured."""
    def __init__(self, message: str, setup_instructions: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.setup_instructions = setup_instructions


class TranslationExecutionError(Exception):
    """Raised when translation fails during model inference."""
    def __init__(
        self,
        message: str,
        error_type: str = "TranslationExecutionError",
        can_switch_provider: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.can_switch_provider = can_switch_provider


@dataclass
class TranslationResult:
    translated_code: str
    explanation: str
    warnings: List[str] = field(default_factory=list)
    model: str = ""
    provider_name: str = ""
    execution_time_ms: Optional[float] = None


class BaseTranslationProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., 'ollama', 'mock')."""
        pass

    @abstractmethod
    async def get_status(self) -> ProviderStatusResponse:
        """Check if the provider and its configured model are currently available."""
        pass

    @abstractmethod
    async def translate(
        self,
        source_lang: Language,
        target_lang: Language,
        code: str,
        instructions: Optional[str] = None
    ) -> TranslationResult:
        """Translate source code between source_lang and target_lang."""
        pass
